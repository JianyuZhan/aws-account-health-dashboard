# Infrastructure Deployment with AWS CDK

This project uses AWS Cloud Development Kit (CDK) to define and deploy infrastructure. This guide covers the initial setup and subsequent updates to the infrastructure stack.

## Prerequisites

1.  **Node.js and npm**: AWS CDK requires Node.js. Ensure that you have Node.js 14.x or later. You can download and install it from [Node.js official website](https://nodejs.org/).
2. **AWS CLI**: Ensure that you have the AWS CLI installed and configured. You can download and install it from [AWS CLI official website](https://aws.amazon.com/cli/).

## Initial Setup

### Step 1: Install AWS CDK CLI

Open a terminal and run the following command to install AWS CDK CLI:

```sh
npm install -g aws-cdk
```

### Step 2: Configure AWS CLI

Run the following command to configure AWS CLI:

```sh
aws configure
```

Follow the prompts to input your AWS Access Key ID, Secret Access Key, default region, and output format.

### Step 3: Create and Activate Python Virtual Environment (Optional but Recommended)

Navigate to the `deploy` directory and create a virtual environment:

```sh
cd deploy/
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
```

### Step 4: Install Project Dependencies

Run the following command to install the required Python packages:

```sh
pip install -r requirements.txt
```

### Step 5: Bootstrap the CDK Environment

Run the following command to bootstrap the CDK environment:

```sh
cdk bootstrap
```

### Step 6: Deploy the CDK Stack

Run the following command to deploy the CDK stack:

```sh
cdk deploy
```

## Updating the Infrastructure Stack

Whenever you make changes to the infrastructure stack, follow these steps to update the deployed resources:

### Step 1: Activate the Virtual Environment (if not already active)

If you haven't already activated the virtual environment, do so now:

```sh
cd deploy/
source .env/bin/activate  # On Windows, use `.env\Scripts\activate`
```

### Step 2: Install Updated Dependencies (if any)

If you have added new dependencies, make sure to install them:

```sh
pip install -r requirements.txt
```

### Step 3: Deploy the Updated Stack

Run the following command to deploy the updated stack:

```sh
cdk init app --language python
cdk deploy
```

This will update the infrastructure with the changes you have made in the CDK stack.

## Additional Commands

- **cdk synth**: Emits the synthesized CloudFormation template.
- **cdk diff**: Compares the specified stack with the deployed stack (or a saved template).

## Troubleshooting

If you encounter any issues, ensure that:
- You have the correct permissions to deploy resources to your AWS account.
- Your AWS credentials are correctly configured.
- All necessary dependencies are installed.

For further assistance, refer to the [AWS CDK documentation](https://docs.aws.amazon.com/cdk/latest/guide/home.html).

