from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
from typing import Dict, List
import asyncio
from datetime import datetime

from models import (
    BareMetalRequest,
    ProvisioningResponse,
    ProvisioningStatus,
    CloudProvider,
    AWSInstanceConfig,
    OCIInstanceConfig
)
from services.airflow import AirflowService

app = FastAPI(title="Bare Metal Provisioning API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Airflow service
airflow_service = AirflowService()

# In-memory storage for requests (replace with database in production)
requests: Dict[str, Dict] = {}

@app.post("/provision", response_model=ProvisioningResponse)
async def create_provisioning_request(request: BareMetalRequest):
    request_id = str(uuid.uuid4())
    
    # Validate provider-specific configuration
    if request.cloud_provider == CloudProvider.AWS and not isinstance(request.provider_config, AWSInstanceConfig):
        raise HTTPException(status_code=400, detail="AWS configuration is required for AWS provider")
    elif request.cloud_provider == CloudProvider.OCI and not isinstance(request.provider_config, OCIInstanceConfig):
        raise HTTPException(status_code=400, detail="OCI configuration is required for OCI provider")
    
    try:
        # Trigger Airflow DAG
        dag_run = airflow_service.trigger_dag(request.dict())
        
        # Store request details with DAG run ID
        requests[request_id] = {
            "request": request.dict(),
            "status": ProvisioningStatus.IN_PROGRESS,
            "created_at": datetime.utcnow(),
            "message": "Request received and DAG triggered",
            "dag_run_id": dag_run["dag_run_id"]
        }
        
        return ProvisioningResponse(
            request_id=request_id,
            status=ProvisioningStatus.IN_PROGRESS,
            message="Request received and DAG triggered",
            instance_details={"dag_run_id": dag_run["dag_run_id"]}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger DAG: {str(e)}")

@app.get("/status/{request_id}", response_model=ProvisioningResponse)
async def get_provisioning_status(request_id: str):
    if request_id not in requests:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request_data = requests[request_id]
    
    try:
        # Get DAG run status from Airflow
        dag_run_status = airflow_service.get_dag_run_status(request_data["dag_run_id"])
        
        # Update status based on DAG run state
        if dag_run_status["state"] == "success":
            request_data["status"] = ProvisioningStatus.COMPLETED
            request_data["message"] = "Instance provisioning completed successfully"
        elif dag_run_status["state"] == "failed":
            request_data["status"] = ProvisioningStatus.FAILED
            request_data["message"] = "Instance provisioning failed"
        elif dag_run_status["state"] in ["running", "queued"]:
            request_data["status"] = ProvisioningStatus.IN_PROGRESS
            request_data["message"] = "Instance provisioning in progress"
        
        if "outputs" in dag_run_status:
            request_data["instance_details"] = dag_run_status["outputs"]
        
    except Exception as e:
        request_data["message"] = f"Error checking status: {str(e)}"
    
    return ProvisioningResponse(
        request_id=request_id,
        status=request_data["status"],
        message=request_data["message"],
        instance_details=request_data.get("instance_details")
    )

@app.get("/requests", response_model=List[ProvisioningResponse])
async def list_provisioning_requests():
    return [
        ProvisioningResponse(
            request_id=request_id,
            status=data["status"],
            message=data["message"],
            instance_details=data.get("instance_details")
        )
        for request_id, data in requests.items()
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 