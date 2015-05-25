# docker-wrapper-py [![Build status](https://ci.frigg.io/badges/frigg/docker-wrapper-py/)](https://ci.frigg.io/frigg/docker-wrapper-py/last/) [![Coverage status](https://ci.frigg.io/badges/coverage/frigg/docker-wrapper-py/)](https://ci.frigg.io/frigg/docker-wrapper-py/last/)

[![Join the chat at https://gitter.im/frigg/docker-wrapper-py](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/frigg/docker-wrapper-py?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

## Install

    pip install docker-wrapper

## Usage

Use it in a with statement:
```python
with Docker() as docker:
    docker.run('command')
```

or as a decorator:
```python
    @Docker.wrap()
    def run_command_in_container(command, docker)
        docker.run(command)
```

Read the documentation on [docker-wrapper-py.readthedocs.org](http://docker-wrapper-py.readthedocs.org)
for more information about how to use this.

--------------

MIT © frigg.io

