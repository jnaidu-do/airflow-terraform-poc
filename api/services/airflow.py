import requests
import base64
from typing import Dict, Any
from config import get_settings

class AirflowService:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.AIRFLOW_API_URL
        auth_string = f"{self.settings.AIRFLOW_USERNAME}:{self.settings.AIRFLOW_PASSWORD}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_b64}"
        }

    def trigger_dag(self, conf: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a DAG with the given configuration
        """
        url = f"{self.base_url}/dags/{self.settings.AIRFLOW_DAG_ID}/dagRuns"
        
        # Format the configuration for the DAG
        dag_conf = {
            "cloud_provider": conf["cloud_provider"],
            "provider_config": conf["provider_config"],
            "instance_name_prefix": conf["instance_name_prefix"],
            "count": conf["count"]
        }
        
        payload = {
            "conf": dag_conf,
            "note": "Triggered via API"
        }
        
        response = requests.post(
            url,
            headers=self.headers,
            json=payload
        )
        
        if response.status_code not in (200, 201):
            raise Exception(f"Failed to trigger DAG: {response.text}")
        
        return response.json()

    def get_dag_run_status(self, dag_run_id: str) -> Dict[str, Any]:
        """
        Get the status of a DAG run
        """
        url = f"{self.base_url}/dags/{self.settings.AIRFLOW_DAG_ID}/dagRuns/{dag_run_id}"
        
        response = requests.get(
            url,
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get DAG run status: {response.text}")
        
        return response.json() 