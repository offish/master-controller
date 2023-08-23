# master-controller
The master controller of Hydroplant which sends records to DB, connects the sensors and actuators with the GUI and vice versa.

## Setup
```bash
git clone git@github.com:hydroplantno/master-controller.git
cd master-controller
pip install -r "requirements.txt"
```

## Running
```bash
# master-controller/
docker start emqx
python3 main.py
```
