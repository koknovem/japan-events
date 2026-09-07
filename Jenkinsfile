pipeline {
  agent any

  options {
    timestamps()
  }

  environment {
    COMPOSE_PROJECT_NAME = 'japan-events'
    COMPOSE_DOCKER_CLI_BUILD = '1'
    DOCKER_BUILDKIT = '1'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build images') {
      steps {
        script { compose('build') }
      }
    }

    stage('Test') {
      steps {
        script { compose('run --rm --no-deps api python -m pytest -q') }
      }
    }

    stage('Start stack') {
      steps {
        script {
          compose('down --remove-orphans')
          compose('up -d --remove-orphans --wait --wait-timeout 180')
        }
      }
    }

    stage('Smoke') {
      steps {
        script {
          retry(12) {
            sleep 5
            compose("exec -T api python -c \"from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/health', timeout=5)\"")
          }
          retry(12) {
            sleep 5
            compose('exec -T web wget -qO- http://127.0.0.1/ >/dev/null')
          }
        }
      }
    }
  }

  post {
    failure {
      script {
        try {
          compose('logs --no-color --tail=200')
        } catch (ignored) {
          echo 'Could not collect compose logs.'
        }
      }
    }
    success {
      echo 'Stack is up: https://japan-events.brian-li.com  (host UI http://127.0.0.1:5173; API is internal, use /api via the UI)'
    }
  }
}

def compose(String args) {
  if (isUnix()) {
    sh "docker compose ${args}"
  } else {
    bat "docker compose ${args}"
  }
}
