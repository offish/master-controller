# master-controller
The master controller of Hydroplant which contains the autonomy logic, logs and adds data to MongoDB, connects the sensors and actuators with the GUI and vice versa.

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

## Testing
```bash
# master-controller/
python -m unittest
```

<!-- ## Run GitHub Actions
```bash
# @hydro-plant-web-server
# actions-runner/
nohup ./run.sh &
``` -->

## Documentation
### Building
Build documentation locally
```bash
# master-controller/docs/
.\make.bat clean
.\make.bat html
```

### Writing
We will use Python type annotations and follow [Google's style](https://google.github.io/styleguide/pyguide.html#383-functions-and-methods). Read more about it [here](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#type-annotations).

Example:
```python
def func(arg1: int, arg2: str) -> bool:
    """Summary line.

    Extended description of function.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    """
    return True

class Class:
    """Summary line.

    Extended description of class

    Attributes:
        attr1: Description of attr1
        attr2: Description of attr2
    """

    attr1: int
    attr2: str
```

