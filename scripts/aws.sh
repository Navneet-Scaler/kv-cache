#!/bin/bash
# =============================================================================
# KV-Cache AWS Deployment Script
# =============================================================================
# Consolidated script for all AWS operations.
#
# Usage:
#   ./aws.sh create     - Create EC2 instances
#   ./aws.sh deploy     - Deploy Docker image to server
#   ./aws.sh test       - Run load test from client
#   ./aws.sh ssh server - SSH into server instance
#   ./aws.sh ssh client - SSH into client instance
#   ./aws.sh results    - Download test results
#   ./aws.sh teardown   - Terminate all resources (IMPORTANT!)
#   ./aws.sh status     - Show instance status
#
# First time setup:
#   cp config.sh.example config.sh
#   nano config.sh  # Set your DOCKER_IMAGE
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

load_config() {
    if [[ ! -f "$SCRIPT_DIR/config.sh" ]]; then
        error "config.sh not found! Run: cp config.sh.example config.sh"
    fi
    source "$SCRIPT_DIR/config.sh"

    if [[ "$DOCKER_IMAGE" == "YOUR_DOCKERHUB_USERNAME/kv-cache:latest" ]]; then
        error "Please update DOCKER_IMAGE in config.sh"
    fi
}

load_instances() {
    if [[ ! -f "$SCRIPT_DIR/.instances" ]]; then
        error "No instances found. Run: ./aws.sh create"
    fi
    source "$SCRIPT_DIR/.instances"
}

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10"

# -----------------------------------------------------------------------------
# Command: create
# -----------------------------------------------------------------------------
cmd_create() {
    load_config

    echo "========================================"
    echo "  Creating AWS Instances"
    echo "========================================"
    info "Region: $AWS_REGION"
    info "Instance type: $INSTANCE_TYPE"

    # Get latest Amazon Linux 2023 AMI
    if [[ -z "$AMI_ID" ]]; then
        info "Finding latest Amazon Linux 2023 AMI..."
        AMI_ID=$(aws ec2 describe-images \
            --region "$AWS_REGION" \
            --owners amazon \
            --filters "Name=name,Values=al2023-ami-2023*-x86_64" \
                      "Name=state,Values=available" \
            --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
            --output text)
        [[ -z "$AMI_ID" || "$AMI_ID" == "None" ]] && error "Could not find AMI"
    fi
    info "Using AMI: $AMI_ID"

    # Create key pair
    KEY_FILE="$HOME/.ssh/${KEY_NAME}.pem"
    if aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$AWS_REGION" &>/dev/null; then
        warn "Key pair '$KEY_NAME' already exists"
        [[ ! -f "$KEY_FILE" ]] && error "Key file not found at $KEY_FILE"
    else
        info "Creating key pair: $KEY_NAME"
        aws ec2 create-key-pair \
            --key-name "$KEY_NAME" \
            --region "$AWS_REGION" \
            --query 'KeyMaterial' \
            --output text > "$KEY_FILE"
        chmod 600 "$KEY_FILE"
    fi

    # Get default VPC
    VPC_ID=$(aws ec2 describe-vpcs --region "$AWS_REGION" \
        --filters "Name=isDefault,Values=true" \
        --query 'Vpcs[0].VpcId' --output text)
    [[ -z "$VPC_ID" || "$VPC_ID" == "None" ]] && error "No default VPC found"

    # Create security group
    SG_ID=$(aws ec2 describe-security-groups --region "$AWS_REGION" \
        --filters "Name=group-name,Values=$SECURITY_GROUP" \
        --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || echo "")

    if [[ -z "$SG_ID" || "$SG_ID" == "None" ]]; then
        info "Creating security group: $SECURITY_GROUP"
        SG_ID=$(aws ec2 create-security-group \
            --group-name "$SECURITY_GROUP" \
            --description "KV-Cache load testing" \
            --vpc-id "$VPC_ID" \
            --region "$AWS_REGION" \
            --query 'GroupId' --output text)

        MY_IP=$(curl -s https://checkip.amazonaws.com)
        aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
            --protocol tcp --port 22 --cidr "${MY_IP}/32" --region "$AWS_REGION" >/dev/null
        aws ec2 authorize-security-group-ingress --group-id "$SG_ID" \
            --protocol tcp --port 7171 --source-group "$SG_ID" --region "$AWS_REGION" >/dev/null
    else
        warn "Security group '$SECURITY_GROUP' already exists"
    fi

    # Launch instances
    info "Launching server instance..."
    SERVER_ID=$(aws ec2 run-instances \
        --image-id "$AMI_ID" --instance-type "$INSTANCE_TYPE" \
        --key-name "$KEY_NAME" --security-group-ids "$SG_ID" \
        --region "$AWS_REGION" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=kv-cache-server},{Key=Project,Value=kv-cache}]" \
        --query 'Instances[0].InstanceId' --output text)

    info "Launching client instance..."
    CLIENT_ID=$(aws ec2 run-instances \
        --image-id "$AMI_ID" --instance-type "$INSTANCE_TYPE" \
        --key-name "$KEY_NAME" --security-group-ids "$SG_ID" \
        --region "$AWS_REGION" \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=kv-cache-client},{Key=Project,Value=kv-cache}]" \
        --query 'Instances[0].InstanceId' --output text)

    info "Waiting for instances..."
    aws ec2 wait instance-running --instance-ids "$SERVER_ID" "$CLIENT_ID" --region "$AWS_REGION"

    # Get IPs
    SERVER_IP=$(aws ec2 describe-instances --instance-ids "$SERVER_ID" --region "$AWS_REGION" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
    SERVER_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids "$SERVER_ID" --region "$AWS_REGION" \
        --query 'Reservations[0].Instances[0].PrivateIpAddress' --output text)
    CLIENT_IP=$(aws ec2 describe-instances --instance-ids "$CLIENT_ID" --region "$AWS_REGION" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

    # Save instance info
    cat > "$SCRIPT_DIR/.instances" << EOF
SERVER_INSTANCE_ID=$SERVER_ID
CLIENT_INSTANCE_ID=$CLIENT_ID
SERVER_IP=$SERVER_IP
SERVER_PRIVATE_IP=$SERVER_PRIVATE_IP
CLIENT_IP=$CLIENT_IP
SECURITY_GROUP_ID=$SG_ID
KEY_FILE=$KEY_FILE
AWS_REGION=$AWS_REGION
EOF

    echo
    echo "========================================"
    echo "  Instances Created!"
    echo "========================================"
    echo "Server: $SERVER_IP (private: $SERVER_PRIVATE_IP)"
    echo "Client: $CLIENT_IP"
    echo
    echo "Next: ./aws.sh deploy"
    echo
    warn "REMEMBER: Run './aws.sh teardown' when done! (~\$0.04/hr)"
}

# -----------------------------------------------------------------------------
# Command: deploy
# -----------------------------------------------------------------------------
cmd_deploy() {
    load_config
    load_instances

    echo "========================================"
    echo "  Deploying to Server"
    echo "========================================"
    info "Server: $SERVER_IP"
    info "Image: $DOCKER_IMAGE"

    # Wait for SSH
    info "Waiting for SSH..."
    for i in {1..30}; do
        ssh $SSH_OPTS -i "$KEY_FILE" ec2-user@"$SERVER_IP" "echo ok" &>/dev/null && break
        sleep 2
    done

    # Install Docker and deploy
    info "Installing Docker and deploying..."
    ssh $SSH_OPTS -i "$KEY_FILE" ec2-user@"$SERVER_IP" << EOF
        set -e
        if ! command -v docker &>/dev/null; then
            sudo yum update -y && sudo yum install -y docker
            sudo systemctl start docker && sudo systemctl enable docker
        fi
        sudo docker pull $DOCKER_IMAGE
        sudo docker stop kv-cache 2>/dev/null || true
        sudo docker rm kv-cache 2>/dev/null || true
        sudo docker run -d --name kv-cache -p 7171:7171 --restart unless-stopped $DOCKER_IMAGE
        sleep 2
        echo "PUT test hello" | nc -w 2 localhost 7171 | grep -q "OK" && echo "Server responding!" || echo "Warning: Server may not be ready"
EOF

    echo
    info "Deployment complete!"
    echo "Next: ./aws.sh test"
}

# -----------------------------------------------------------------------------
# Command: test
# -----------------------------------------------------------------------------
cmd_test() {
    load_config
    load_instances

    echo "========================================"
    echo "  Running Load Test"
    echo "========================================"
    info "Target: $SERVER_PRIVATE_IP:7171"
    info "Connections: ${LOAD_TEST_CONNECTIONS:-100}"
    info "Requests: ${LOAD_TEST_REQUESTS:-1000}"

    # Wait for SSH
    for i in {1..30}; do
        ssh $SSH_OPTS -i "$KEY_FILE" ec2-user@"$CLIENT_IP" "echo ok" &>/dev/null && break
        sleep 2
    done

    # Setup client
    ssh $SSH_OPTS -i "$KEY_FILE" ec2-user@"$CLIENT_IP" "
        command -v python3 &>/dev/null || sudo yum install -y python3
        mkdir -p ~/load_test
    "

    # Copy and run load test
    scp $SSH_OPTS -i "$KEY_FILE" "$PROJECT_DIR/scripts/load_test.py" ec2-user@"$CLIENT_IP":~/load_test/

    ssh $SSH_OPTS -i "$KEY_FILE" ec2-user@"$CLIENT_IP" "
        cd ~/load_test
        python3 load_test.py \
            --host $SERVER_PRIVATE_IP --port 7171 \
            --connections ${LOAD_TEST_CONNECTIONS:-100} \
            --requests ${LOAD_TEST_REQUESTS:-1000} \
            --ratio ${LOAD_TEST_RATIO:-0.5} \
            --output results.json
    "

    # Download results
    mkdir -p "$PROJECT_DIR/results"
    scp $SSH_OPTS -i "$KEY_FILE" ec2-user@"$CLIENT_IP":~/load_test/results.json \
        "$PROJECT_DIR/results/load_test_results.json"

    echo
    info "Results saved to: results/load_test_results.json"
    warn "REMEMBER: Run './aws.sh teardown' when done!"
}

# -----------------------------------------------------------------------------
# Command: ssh
# -----------------------------------------------------------------------------
cmd_ssh() {
    load_instances

    case "$1" in
        server)
            info "Connecting to server: $SERVER_IP"
            exec ssh $SSH_OPTS -i "$KEY_FILE" ec2-user@"$SERVER_IP"
            ;;
        client)
            info "Connecting to client: $CLIENT_IP"
            exec ssh $SSH_OPTS -i "$KEY_FILE" ec2-user@"$CLIENT_IP"
            ;;
        *)
            error "Usage: ./aws.sh ssh [server|client]"
            ;;
    esac
}

# -----------------------------------------------------------------------------
# Command: results
# -----------------------------------------------------------------------------
cmd_results() {
    load_instances

    mkdir -p "$PROJECT_DIR/results"
    scp $SSH_OPTS -i "$KEY_FILE" ec2-user@"$CLIENT_IP":~/load_test/results.json \
        "$PROJECT_DIR/results/load_test_results.json" 2>/dev/null || error "No results found"

    info "Results downloaded to: results/load_test_results.json"
    echo
    python3 -c "
import json
with open('$PROJECT_DIR/results/load_test_results.json') as f:
    r = json.load(f)
print(f\"Throughput:   {r.get('requests_per_second', 0):,.0f} req/s\")
print(f\"Mean latency: {r.get('latency_mean', 0):.2f} ms\")
print(f\"P99 latency:  {r.get('latency_p99', 0):.2f} ms\")
print(f\"Error rate:   {r.get('error_rate', 0):.2f}%\")
" 2>/dev/null || cat "$PROJECT_DIR/results/load_test_results.json"
}

# -----------------------------------------------------------------------------
# Command: status
# -----------------------------------------------------------------------------
cmd_status() {
    load_instances

    echo "========================================"
    echo "  Instance Status"
    echo "========================================"
    echo "Server: $SERVER_IP (ID: $SERVER_INSTANCE_ID)"
    echo "Client: $CLIENT_IP (ID: $CLIENT_INSTANCE_ID)"
    echo "Region: $AWS_REGION"
    echo

    aws ec2 describe-instances --instance-ids "$SERVER_INSTANCE_ID" "$CLIENT_INSTANCE_ID" \
        --region "$AWS_REGION" \
        --query 'Reservations[].Instances[].[Tags[?Key==`Name`].Value|[0],State.Name,InstanceId]' \
        --output table
}

# -----------------------------------------------------------------------------
# Command: teardown
# -----------------------------------------------------------------------------
cmd_teardown() {
    if [[ ! -f "$SCRIPT_DIR/.instances" ]]; then
        error "No instances found. Nothing to tear down."
    fi
    source "$SCRIPT_DIR/.instances"

    echo "========================================"
    echo "  Teardown AWS Resources"
    echo "========================================"
    warn "This will PERMANENTLY delete:"
    echo "  - Server: $SERVER_INSTANCE_ID"
    echo "  - Client: $CLIENT_INSTANCE_ID"
    echo "  - Security group: $SECURITY_GROUP_ID"
    echo

    read -p "Continue? (y/N) " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Yy]$ ]] && { echo "Aborted."; exit 0; }

    info "Terminating instances..."
    aws ec2 terminate-instances \
        --instance-ids "$SERVER_INSTANCE_ID" "$CLIENT_INSTANCE_ID" \
        --region "$AWS_REGION" >/dev/null

    info "Waiting for termination..."
    aws ec2 wait instance-terminated \
        --instance-ids "$SERVER_INSTANCE_ID" "$CLIENT_INSTANCE_ID" \
        --region "$AWS_REGION"

    info "Deleting security group..."
    for i in {1..5}; do
        aws ec2 delete-security-group --group-id "$SECURITY_GROUP_ID" \
            --region "$AWS_REGION" 2>/dev/null && break
        sleep 5
    done

    rm -f "$SCRIPT_DIR/.instances"

    echo
    info "Teardown complete!"

    # Ask about key pair
    read -p "Delete key pair '$KEY_NAME'? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        aws ec2 delete-key-pair --key-name "$KEY_NAME" --region "$AWS_REGION"
        rm -f "$KEY_FILE"
        info "Key pair deleted."
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
case "${1:-}" in
    create)   cmd_create ;;
    deploy)   cmd_deploy ;;
    test)     cmd_test ;;
    ssh)      cmd_ssh "$2" ;;
    results)  cmd_results ;;
    status)   cmd_status ;;
    teardown) cmd_teardown ;;
    *)
        echo "KV-Cache AWS Deployment Script"
        echo
        echo "Usage: ./aws.sh <command>"
        echo
        echo "Commands:"
        echo "  create    Create EC2 instances"
        echo "  deploy    Deploy Docker image to server"
        echo "  test      Run load test from client"
        echo "  ssh       SSH into instance (./aws.sh ssh server|client)"
        echo "  results   Download test results"
        echo "  status    Show instance status"
        echo "  teardown  Terminate all resources"
        echo
        echo "Setup: cp config.sh.example config.sh && nano config.sh"
        ;;
esac
