# Microservices deployment on VMs

## Prerequsites

* We have Ubuntu server which has python3 installed by default
* Run below step to setup python virtual environment to host microservices
```
sudo apt update
sudo apt install -y python3-full python3-venv python3-pip build-essential
cd /root
mkdir microservices
cd  microservices
python3 -m venv venv
source venv/bin/activate
(venv) jegadeesh@server1:root/microservices$
pip install fastapi uvicorn requests gunicorn
python -c "import fastapi, uvicorn; print('OK')"
```

* Repeat above steps in Server2 VM as well

## VM Server1

* Login to server1 from local MAC using SSH
* Switch as root user and move to /root/microservice directory
* copy service_1.py file to the directory, Ensure to update server2 IP. EX: 192.168.1.5
* Run below command to start the microservice 1 in server 1
```
source venv/bin/activate
(venv) root@Server1:~/microservices# uvicorn service_1:app --host 0.0.0.0 --port 8000
```
## VM server2
* Login to server2 from local MAC using SSH
* Switch as root user and move to /root/microservice directory
* copy service_2.py file to the directory
* Run below command to start the microservice2 in server2
```
source venv/bin/activate
(venv) root@Server2:~/microservices# uvicorn service_2:app --host 0.0.0.0 --port 9000
```
