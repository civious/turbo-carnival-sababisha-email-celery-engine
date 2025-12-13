pipeline {
    agent any

    environment {
        // Project settings
        PROJECT_NAME = 'sababisha-celery'
        DEPLOY_PATH = '/opt/sababisha-celery'

        // Docker settings
        COMPOSE_PROJECT_NAME = 'sababisha-celery'

        // Git settings
        GIT_BRANCH = 'main'
    }

    stages {
        stage('Cleanup Workspace') {
            steps {
                echo 'Cleaning workspace...'
                cleanWs()
            }
        }

        stage('Checkout') {
            steps {
                echo 'Checking out code from repository...'
                checkout scm
            }
        }

        stage('Verify Environment') {
            steps {
                echo 'Verifying deployment environment...'
                sh '''
                    # Check if deployment directory exists
                    if [ ! -d "${DEPLOY_PATH}" ]; then
                        echo "Creating deployment directory: ${DEPLOY_PATH}"
                        sudo mkdir -p ${DEPLOY_PATH}
                        sudo chown -R jenkins:jenkins ${DEPLOY_PATH}
                    fi

                    # Check if .env exists
                    if [ ! -f "${DEPLOY_PATH}/.env" ]; then
                        echo "ERROR: .env file not found at ${DEPLOY_PATH}/.env"
                        echo "Please create .env file with required credentials before deploying"
                        exit 1
                    fi

                    # Check if Images directory exists
                    if [ ! -d "${DEPLOY_PATH}/Images" ]; then
                        echo "Creating Images directory"
                        mkdir -p ${DEPLOY_PATH}/Images
                    fi

                    # Verify Docker is running
                    docker ps > /dev/null 2>&1 || {
                        echo "ERROR: Docker is not running or not accessible"
                        exit 1
                    }

                    echo "Environment verification complete"
                '''
            }
        }

        stage('Stop Running Containers') {
            steps {
                echo 'Stopping running containers...'
                sh '''
                    cd ${DEPLOY_PATH} || exit 1

                    # Stop and remove existing containers
                    if [ -f docker-compose.yml ]; then
                        docker-compose down || true
                    fi

                    # Remove old containers if they exist
                    docker rm -f sababisha-celery-email-worker sababisha-celery-log-worker sababisha-celery-beat 2>/dev/null || true

                    echo "Containers stopped"
                '''
            }
        }

        stage('Deploy Application Files') {
            steps {
                echo 'Deploying application files...'
                sh '''
                    # Copy all files except .env and Images
                    rsync -av --exclude='.env' \
                              --exclude='Images/' \
                              --exclude='logs/' \
                              --exclude='venv/' \
                              --exclude='.git/' \
                              --exclude='__pycache__/' \
                              --exclude='*.pyc' \
                              --exclude='celerybeat-schedule' \
                              ${WORKSPACE}/ ${DEPLOY_PATH}/

                    # Set proper permissions
                    sudo chown -R jenkins:jenkins ${DEPLOY_PATH}
                    chmod +x ${DEPLOY_PATH}/start_celery.sh 2>/dev/null || true

                    echo "Application files deployed"
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                echo 'Building Docker images...'
                sh '''
                    cd ${DEPLOY_PATH}

                    # Build Docker image
                    docker-compose build --no-cache

                    echo "Docker images built successfully"
                '''
            }
        }

        stage('Start Services') {
            steps {
                echo 'Starting Celery services...'
                sh '''
                    cd ${DEPLOY_PATH}

                    # Start services in detached mode
                    docker-compose up -d

                    # Wait for services to start
                    sleep 10

                    echo "Services started"
                '''
            }
        }

        stage('Health Check') {
            steps {
                echo 'Performing health checks...'
                sh '''
                    cd ${DEPLOY_PATH}

                    # Check if containers are running
                    echo "Checking container status..."
                    docker-compose ps

                    # Wait for workers to be ready
                    echo "Waiting for workers to initialize..."
                    sleep 5

                    # Check worker health
                    echo "Checking worker health..."
                    docker-compose exec -T celery-email-worker celery -A celery_config:app inspect ping || {
                        echo "WARNING: Email worker health check failed"
                    }

                    echo "Health check complete"
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                echo 'Verifying deployment...'
                sh '''
                    cd ${DEPLOY_PATH}

                    # Show running containers
                    echo "=== Running Containers ==="
                    docker ps --filter "name=sababisha-celery"

                    # Show recent logs
                    echo "=== Recent Logs ==="
                    docker-compose logs --tail=50

                    echo "Deployment verification complete"
                '''
            }
        }
    }

    post {
        success {
            echo 'Deployment completed successfully!'
            sh '''
                echo "=========================================="
                echo "Deployment Summary"
                echo "=========================================="
                echo "Project: ${PROJECT_NAME}"
                echo "Deploy Path: ${DEPLOY_PATH}"
                echo "Branch: ${GIT_BRANCH}"
                echo "Build Number: ${BUILD_NUMBER}"
                echo "=========================================="
                echo "Services Status:"
                cd ${DEPLOY_PATH}
                docker-compose ps
                echo "=========================================="
            '''
        }

        failure {
            echo 'Deployment failed!'
            sh '''
                echo "=========================================="
                echo "Deployment Failed - Troubleshooting Info"
                echo "=========================================="
                cd ${DEPLOY_PATH}

                echo "Container Status:"
                docker ps -a --filter "name=sababisha-celery"

                echo ""
                echo "Recent Logs:"
                docker-compose logs --tail=100

                echo "=========================================="
            '''
        }

        always {
            echo 'Cleaning up workspace...'
            cleanWs()
        }
    }
}
