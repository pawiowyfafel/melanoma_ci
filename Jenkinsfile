// Jenkinsfile
// Pipeline dla projektu DermaScan
//
// Etapy:
//  1. Checkout
//  2. Test Backend (pytest)
//  3. Test Frontend (jest)
//  4. Build obrazów Docker
//  5. Push do lokalnego rejestru (VM1:5000)
//  6. Deploy na VM3 przez Ansible
//  7. Testy E2E
//  8. Post-actions (notify)

pipeline {
    agent none   // każdy stage deklaruje własnego agenta

    environment {
        REGISTRY  = "192.168.56.10:5000"
        VM2_IP    = "192.168.56.20"
        VM3_IP    = "192.168.56.30"
        IMG_FRONT = "${REGISTRY}/melanoma-frontend"
        IMG_BACK  = "${REGISTRY}/melanoma-backend"
        TAG       = "${BUILD_NUMBER}"
    }

    options {
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        // ── 1. Checkout ──────────────────────────────────────────────────────
        stage('Checkout') {
            agent { label 'build-agent' }   // VM2
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: "git rev-parse --short HEAD",
                        returnStdout: true
                    ).trim()
                    echo "Commit: ${env.GIT_COMMIT_SHORT} | Build: ${TAG}"
                }
            }
        }

        // ── 2. Testy backendu ────────────────────────────────────────────────
        stage('Test Backend') {
            agent { label 'build-agent' }
            steps {
                dir('backend') {
                    sh '''
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install --quiet -r requirements.txt pytest pillow
                        pytest tests/ -v --tb=short \
                               --junitxml=../test-results/backend.xml
                    '''
                }
            }
            post {
                always {
                    junit 'test-results/backend.xml'
                }
            }
        }

        // ── 3. Testy frontendu ───────────────────────────────────────────────
        stage('Test Frontend') {
            agent { label 'build-agent' }
            steps {
                dir('frontend/tests') {
                    sh '''
                        npm install --silent
                        npm install jest-junit --silent
                        JEST_JUNIT_OUTPUT_DIR=. JEST_JUNIT_OUTPUT_NAME=junit.xml npx jest --ci --reporters=default --reporters=jest-junit || true
                    '''
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'frontend/tests/junit.xml'
                }
            }
        }

        // ── 4. Build obrazów ─────────────────────────────────────────────────
        stage('Build Images') {
            parallel {
                stage('Build Frontend') {
                    agent { label 'build-agent' }
                    steps {
                        sh "docker build -t ${IMG_FRONT}:${TAG} -t ${IMG_FRONT}:latest ./frontend"
                    }
                }
                stage('Build Backend') {
                    agent { label 'build-agent' }
                    steps {
                        sh "docker build -t ${IMG_BACK}:${TAG} -t ${IMG_BACK}:latest ./backend"
                    }
                }
            }
        }

        // ── 5. Push do rejestru ──────────────────────────────────────────────
        stage('Push to Registry') {
            agent { label 'build-agent' }
            steps {
                sh """
                    docker push ${IMG_FRONT}:${TAG}
                    docker push ${IMG_FRONT}:latest
                    docker push ${IMG_BACK}:${TAG}
                    docker push ${IMG_BACK}:latest
                """
            }
        }

        // ── 6. Deploy (Ansible z VM1) ────────────────────────────────────────
        stage('Deploy to Production') {
            agent { label 'built-in' }   // VM1 — ma Ansible
            steps {
                sh """
                    export LANG=en_US.UTF-8
                    export LC_ALL=en_US.UTF-8
                    ansible-playbook \
                        -i ansible/inventory.ini \
                        ansible/deploy.yml \
                        -e "image_tag=${TAG}" \
                        -e "registry=${REGISTRY}" \
                        -e "vm2_ip=${VM2_IP}"
                """
            }
        }

        // ── 7. Testy E2E ─────────────────────────────────────────────────────
        stage('E2E Tests') {
            agent { label 'build-agent' }
            steps {
                sh """
                    python3 -m venv .venv-e2e
                    . .venv-e2e/bin/activate
                    pip install --quiet pytest requests pillow
                    FRONTEND_URL=http://${VM3_IP} \
                    BACKEND_URL=http://${VM3_IP}:8080 \
                    pytest tests/e2e/ -v --tb=short \
                           --junitxml=test-results/e2e.xml
                """
            }
            post {
                always {
                    junit 'test-results/e2e.xml'
                }
            }
        }
    }

    // ── Post-actions ─────────────────────────────────────────────────────────
    post {
        success {
            echo "✅ Pipeline #${BUILD_NUMBER} zakończony sukcesem! Tag: ${TAG}"
            // Tu możesz dodać powiadomienie Slack / email
        }
        failure {
            echo "❌ Pipeline #${BUILD_NUMBER} FAILED. Sprawdź logi."
        }
        always {
            node('build-agent') {
                // Wyczyść stare obrazy (zostaw 3 ostatnie)
                sh """
                    docker images ${IMG_FRONT} --format '{{.Tag}}' | \
                        sort -rn | tail -n +4 | \
                        xargs -I{} docker rmi ${IMG_FRONT}:{} || true
                    docker images ${IMG_BACK} --format '{{.Tag}}' | \
                        sort -rn | tail -n +4 | \
                        xargs -I{} docker rmi ${IMG_BACK}:{} || true
                """
            }
        }
    }
}
