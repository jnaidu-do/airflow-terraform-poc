FROM apache/airflow:2.7.1

USER root

# Install Terraform
RUN apt-get update && \
    apt-get install -y curl unzip && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        curl -fsSL https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_amd64.zip -o terraform.zip; \
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        curl -fsSL https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_arm64.zip -o terraform.zip; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    unzip terraform.zip && \
    mv terraform /usr/local/bin/ && \
    chown airflow:airflow /usr/local/bin/terraform && \
    chmod 777 /usr/local/bin/terraform && \
    rm terraform.zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a directory for Terraform and set permissions
RUN mkdir -p /opt/airflow/terraform && \
    chown -R airflow:root /opt/airflow/terraform && \
    chmod -R 775 /opt/airflow/terraform

USER airflow 