import logging
import os
import re
import uuid
from time import sleep

from docker.errors import DockerUnavailableError
from docker.helpers import execute

logger = logging.getLogger(__name__)


class Docker(object):
    """
    Docker manager which can start and stop containers in addition to run commands with docker exec.
    The manager also have a few helper functions for things like listing files and directories.
    """

    def __init__(self, image='ubuntu', name_prefix='dyn', timeout=3600, privilege=False,
                 combine_outputs=False):
        """
        Creates a docker manager. Each manager has a reference to a unique container name.

        :param image: The image which the manager should use to start the container. It could be
                      a local image or an image from the registry.
        :type image: str
        :param timeout: The time the docker container will live after running ``docker.start()`` in
                        seconds.
        :type timeout: int
        :param privilege: If set to True the docker container will be run with the privilege
                          parameter.
        :type privilege: bool
        :param combine_outputs: Setting this to True will put stderr output in stdout.
        :type combine_outputs: bool
        :return: A docker manager object.
        :rtype: Docker
        """
        self.container_name = '{0}-{1}'.format(name_prefix, uuid.uuid4())
        self.timeout = timeout
        self.image = image
        self.privilege = privilege
        self.combine_outputs = combine_outputs

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.stop()
        if exc_value:
            raise exc_value

    def run(self, command, working_directory=''):
        """
        Runs the command with docker exec in the given working directory.

        :param command: The command that should be run with docker exec. The command will be wrapped
                        in  `bash -c \'command\'".
        :type command: str
        :param working_directory: The path to the directory where the command should be run. This
                                  will be evaluated with ``_get_working_directory``, thus relative
                                  paths will become absolute paths.
        :type working_directory: str
        :return: A ProcessResult object containing information on the result of the command.
        :rtype: ProcessResult
        """
        working_directory = self._get_working_directory(working_directory)
        command = command.replace('\'', '"')
        command_string = 'cd {working_directory} && {command}'
        if self.combine_outputs:
            command_string += ' 2>&1'
        result = execute(
            'docker exec -i {container} bash -c \'{command} ;  echo "--return-$?--"\''.format(
                container=self.container_name,
                command=command_string.format(working_directory=working_directory, command=command)
            )
        )

        return_code_match = re.search(r'(?:\\n)?--return-(\d+)--$', result.out)
        if return_code_match:
            result.return_code = int(return_code_match.group(1))
            result.out = result.out.replace(return_code_match.group(0), '')
            if result.out.endswith('\n'):
                result.out = result.out[:len(result.out) - 1]
        return result

    def read_file(self, path):
        """
        Reads the content of the file on the given path. Returns None if the file does not exist.
        :param path: The path to the file.
        :type path: str
        :return: The content of the file
        :rtype: str
        """
        path = self._get_working_directory(path)
        result = self.run('cat {0}'.format(path))
        if result.succeeded:
            return result.out
        return None

    def create_file(self, path, content):
        """
        Create file on the given path with the given content
        :param path: The path to the file.
        :type path: str
        :param content: The content of the file.
        :type content: str
        :return: A object with the result of the create command.
        :rtype: ProcessResult
        """
        path = self._get_working_directory(path)
        return self.run('echo "{0}" >> {1}'.format(content, path))

    def file_exist(self, path):
        """
        Checks whether a file exists or not.
        :param path: The path to the file.
        :type path: str
        :rtype: bool
        """
        path = self._get_working_directory(path)
        return self.run('test -f {0}'.format(path)).return_code == 0

    def directory_exist(self, path):
        """
        Checks whether a directory exists or not.
        :param path: The path to the directory.
        :type path: str
        :rtype: bool
        """
        path = self._get_working_directory(path)
        return self.run('test -d {0}'.format(path)).return_code == 0

    def list_files(self, path):
        """
        List files on a given path.
        :param path: The path to the directory.
        :type path: str
        :return: An list of file names
        :rtype: list
        """
        result = []

        path = self._get_working_directory(path)

        for file_path in self.run('ls -m {0}'.format(path)).out.split(', '):
            full_path = os.path.join(path, file_path)
            if self.file_exist(full_path) and not self.directory_exist(full_path):
                result.append(file_path)

        return result

    def list_directories(self, path, include_trailing_slash=True):
        """
        List directories on a given path.
        :param path: The path to the directory.
        :type path: str
        :return: An list of directory names
        :rtype: list
        """
        result = []

        working_directory = self._get_working_directory(path)

        for file_path in self.run('ls -dm */'.format(path), working_directory).out.split(', '):
            if self.directory_exist(os.path.join(path, file_path)):

                if include_trailing_slash:
                    result.append(file_path)
                else:
                    result.append(file_path[:-1])

        return result

    def start(self):
        """
        Starts a container based on the parameters passed to __init__.

        :return: The docker object
        """
        if self.privilege:
            command_string = 'docker run -d --privileged --name {0} {1} /bin/sleep {2}'
        else:
            command_string = 'docker run -d --name {0} {1} /bin/sleep {2}'

        result = execute(command_string.format(
            self.container_name,
            self.image,
            self.timeout
        ))
        if not result.succeeded:
            raise DockerUnavailableError('Starting the docker container failed.')
        return self

    def stop(self):
        """
        Stops the container started by this class instance.

        :return: The docker object
        """
        sleep(2)
        execute('docker kill {0}'.format(self.container_name))
        execute('docker rm {0}'.format(self.container_name))
        return self

    @staticmethod
    def wrap(*wrap_args, **wrap_kwargs):
        """
        Decorator that wraps the function call in a Docker with statement. It
        accepts the same arguments. This decorator adds a docker manager instance
        to the kwargs passed into the decorated function.

        :return: The decorated function.
        """
        def activate(func):
            def wrapper(*args, **kwargs):
                with Docker(*wrap_args, **wrap_kwargs) as docker:
                    kwargs['docker'] = docker
                    return func(*args, **kwargs)

            return wrapper

        return activate

    @staticmethod
    def _get_working_directory(working_directory):
        """
        Gets the path of the working working directory. It takes a path and converts it to an
        appropriate absolute path.
        :param working_directory:
        :type working_directory: str
        :return: An absolute path to the given working directory.
        :rtype str:
        """
        if working_directory.startswith('/') or working_directory.startswith('~/'):
            return working_directory
        return '~/{}'.format(working_directory)
