#!/bin/bash

# Agent Platform Deployment Script
# This script helps deploy and test the agent platform

set -e

echo "🚀 Agent Platform Deployment Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Start infrastructure services
start_infrastructure() {
    print_status "Starting infrastructure services..."
    
    # Start the infrastructure services
    docker-compose up -d rabbitmq postgres redis qdrant minio
    
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check if services are healthy
    if docker-compose ps | grep -q "unhealthy"; then
        print_warning "Some services may not be fully ready. Check docker-compose ps for details."
    else
        print_success "Infrastructure services are running"
    fi
}

# Build and start application services
start_applications() {
    print_status "Building and starting application services..."
    
    # Build the application images
    docker-compose build agent-manager agent-runtime api-gateway
    
    # Start the application services
    docker-compose up -d agent-manager agent-runtime api-gateway
    
    print_status "Waiting for applications to start..."
    sleep 15
    
    print_success "Application services are running"
}

# Start monitoring services
start_monitoring() {
    print_status "Starting monitoring services..."
    
    # Start monitoring stack
    cd monitoring
    docker-compose up -d
    cd ..
    
    print_success "Monitoring services are running"
}

# Test the system
test_system() {
    print_status "Testing the system..."
    
    # Test API Gateway health
    if curl -s http://localhost:8080/health > /dev/null; then
        print_success "API Gateway is responding"
    else
        print_error "API Gateway is not responding"
        return 1
    fi
    
    # Test Agent Manager health
    if curl -s http://localhost:8000/health > /dev/null; then
        print_success "Agent Manager is responding"
    else
        print_error "Agent Manager is not responding"
        return 1
    fi
    
    # Test Agent Runtime health
    if curl -s http://localhost:8001/health > /dev/null; then
        print_success "Agent Runtime is responding"
    else
        print_error "Agent Runtime is not responding"
        return 1
    fi
    
    print_success "All services are healthy!"
}

# Create a test agent
create_test_agent() {
    print_status "Creating a test agent..."
    
    # Create test agent via API Gateway
    response=$(curl -s -X POST http://localhost:8080/agents \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Test Agent",
            "description": "A test autonomous agent",
            "type": "autonomous",
            "capabilities": ["code_generation", "data_analysis"],
            "resources": {"memory": "1GB", "cpu": "1 core"},
            "parameters": {
                "goals": ["Complete assigned tasks efficiently"],
                "constraints": ["Use only approved tools"]
            }
        }')
    
    if echo "$response" | grep -q '"id"'; then
        agent_id=$(echo "$response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
        print_success "Test agent created with ID: $agent_id"
        
        # Create a test task
        print_status "Creating a test task for the agent..."
        task_response=$(curl -s -X POST "http://localhost:8080/tasks" \
            -H "Content-Type: application/json" \
            -d "{
                \"agent_id\": \"$agent_id\",
                \"task_type\": \"generate_code\",
                \"parameters\": {
                    \"description\": \"Hello World program\",
                    \"language\": \"python\"
                }
            }")
        
        if echo "$task_response" | grep -q '"id"'; then
            task_id=$(echo "$task_response" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
            print_success "Test task created with ID: $task_id"
            
            # Wait a bit and check task status
            sleep 5
            task_status=$(curl -s "http://localhost:8080/tasks/$task_id")
            print_status "Task status: $(echo "$task_status" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
        else
            print_error "Failed to create test task"
        fi
    else
        print_error "Failed to create test agent"
        echo "Response: $response"
    fi
}

# Show service URLs
show_urls() {
    echo ""
    echo "🌐 Service URLs:"
    echo "==============="
    echo "API Gateway:      http://localhost:8080"
    echo "Agent Manager:    http://localhost:8000"
    echo "Agent Runtime:    http://localhost:8001"
    echo "RabbitMQ UI:      http://localhost:15672 (guest/guest)"
    echo "Grafana:          http://localhost:3000 (admin/admin_password)"
    echo "Prometheus:       http://localhost:9090"
    echo "MinIO Console:    http://localhost:9001 (agent_platform/agent_platform_password)"
    echo ""
    echo "📚 API Documentation:"
    echo "API Gateway Docs: http://localhost:8080/docs"
    echo "Agent Manager:    http://localhost:8000/docs"
    echo "Agent Runtime:    http://localhost:8001/docs"
}

# Stop all services
stop_services() {
    print_status "Stopping all services..."
    
    docker-compose down
    cd monitoring && docker-compose down && cd ..
    
    print_success "All services stopped"
}

# Clean up everything
cleanup() {
    print_status "Cleaning up..."
    
    docker-compose down -v --remove-orphans
    cd monitoring && docker-compose down -v --remove-orphans && cd ..
    
    # Remove unused images
    docker image prune -f
    
    print_success "Cleanup completed"
}

# Main script logic
case "${1:-start}" in
    "start")
        check_docker
        start_infrastructure
        start_applications
        start_monitoring
        test_system
        create_test_agent
        show_urls
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        sleep 5
        check_docker
        start_infrastructure
        start_applications
        start_monitoring
        test_system
        show_urls
        ;;
    "test")
        test_system
        create_test_agent
        ;;
    "cleanup")
        cleanup
        ;;
    "urls")
        show_urls
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|test|cleanup|urls}"
        echo ""
        echo "Commands:"
        echo "  start    - Start all services and run tests"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  test     - Test the running system"
        echo "  cleanup  - Stop services and clean up volumes/images"
        echo "  urls     - Show service URLs"
        exit 1
        ;;
esac