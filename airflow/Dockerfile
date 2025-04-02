FROM apache/airflow:2.7.1

USER root

# Install Terraform
RUN apt-get update && \
    apt-get install -y curl unzip && \
    curl -fsSL https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_arm64.zip -o terraform.zip && \
    unzip terraform.zip && \
    mv terraform /usr/local/bin/ && \
    rm terraform.zip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER airflow 