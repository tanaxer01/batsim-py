from abc import ABC
from enum import Enum
from typing import Optional
from typing import Sequence
from typing import Union

from pydispatch import dispatcher

from .events import JobEvent
from .utils.commons import Identifier


class JobProfileType(Enum):
    """ Batsim Job Profile Type

        This class enumerates the distinct profiles a job can simulate.
    """
    DELAY = 0
    PARALLEL = 1
    PARALLEL_HOMOGENEOUS = 2
    PARALLEL_HOMOGENEOUS_TOTAL = 3
    COMPOSED = 4
    PARALLEL_HOMOGENEOUS_PFS = 5
    DATA_STAGING = 6

    def __str__(self) -> str:
        return self.name


class JobState(Enum):
    """ Batsim Job State

        This class enumerates the distinct states a job can be in.
    """

    UNKNOWN = 0
    SUBMITTED = 1
    RUNNING = 2
    COMPLETED_SUCCESSFULLY = 3
    COMPLETED_FAILED = 4
    COMPLETED_WALLTIME_REACHED = 5
    COMPLETED_KILLED = 6
    REJECTED = 7
    ALLOCATED = 8

    def __str__(self) -> str:
        return self.name


class JobProfile(ABC):
    """ Batsim Job Profile base class.

    This is the base class for the different profiles a job can execute.

    Args:
        name: The profile name. Must be unique within a workload.
        profile_type: The job profile type.
    Raises:
        TypeError: In case of invalid arguments.
    """

    def __init__(self, name: str, profile_type: JobProfileType) -> None:
        if not isinstance(profile_type, JobProfileType):
            raise TypeError('Expected `profile_type` argument to be an instance'
                            'of `JobProfileType`, got {}'.format(profile_type))

        self.__name = str(name)
        self.__type = profile_type

    @property
    def name(self) -> str:
        """The profile's name. """
        return self.__name

    @property
    def type(self) -> JobProfileType:
        """The profile's type. """
        return self.__type


class DelayJobProfile(JobProfile):
    """ Batsim Delay Job Profile class.

    This class describes a job that will sleep during the defined time.

    Args:
        name: The profile name. Must be unique within a workload.
        delay: The seconds to sleep.
    Raises:
        TypeError: In case of invalid arguments.

    Examples:
        A job that will sleep for 100 seconds.

        >>> profile = DelayJobProfile(name="delay", delay=100)
    """

    def __init__(self, name: str, delay: Union[int, float]) -> None:
        super().__init__(name, JobProfileType.DELAY)
        self.__delay = float(delay)

    @property
    def delay(self) -> float:
        """The time which the job will sleep. """
        return self.__delay


class ParallelJobProfile(JobProfile):
    """ Batsim Parallel Job Profile class.

    This class describes a job that performs a set of computations
    and communications on allocated hosts.

    Args:
        name: The profile name. Must be unique within a workload.
        cpu: A list that defines the amount of flop/s to be 
            computed on each allocated host.
        com: A list [host x host] that defines the amount of bytes 
            to be transferred between allocated hosts.
    Raises:
        TypeError: In case of invalid arguments.
        ValueError: In case of `com` argument invalid size.

    Examples:
        Two hosts computing 10E6 flop/s each with local communication only.

        >>> profile = ParallelJobProfile(name="parallel", cpu=[10e6, 10e6], com=[5e6, 0, 0, 5e6])

        Two hosts computing 2E6 flop/s each with host 1 sending 5E6 bytes to host 2.

        >>> profile = ParallelJobProfile(name="parallel", cpu=[2e6, 2e6], com=[0, 5e6, 0, 0])

        One host computing 2E6 flop/s with host 1 sending 5E6 bytes to host 2 and host 2 sending 10E6 bytes to host 1.

        >>> profile = ParallelJobProfile(name="parallel", cpu=[2e6, 0], com=[0, 5e6, 10e6, 0])
    """

    def __init__(self, name: str, cpu: Sequence[Union[int, float]], com: Sequence[Union[int, float]]) -> None:
        if len(com) != len(cpu) * len(cpu):
            raise ValueError('Expected `com` argument to be a '
                             'list of size [host x host], got {}'.format(com))

        super().__init__(name, JobProfileType.PARALLEL)
        self.__cpu = list(cpu)
        self.__com = list(com)

    @property
    def cpu(self) -> Sequence[Union[int, float]]:
        """The amount of flop/s to be computed on each host."""
        return self.__cpu

    @property
    def com(self) -> Sequence[Union[int, float]]:
        """The amount of bytes to be transferred between hosts."""
        return self.__com


class ParallelHomogeneousJobProfile(JobProfile):
    """ Batsim Parallel Homogeneous Job Profile class.

    This class describes a job that performs the same computation
    and communication on all allocated hosts.

    Args:
        name: The profile name. Must be unique within a workload.
        cpu: The amount of flop/s to be computed on each allocated host.
        com: The amount of bytes to send and receive between each pair of hosts.
    Raises:
        TypeError: In case of invalid arguments.

    Examples:
        >>> profile = ParallelHomogeneousJobProfile("name", cpu=10e6, com=5e6)
    """

    def __init__(self, name: str, cpu: Union[int, float], com: Union[int, float]) -> None:
        super().__init__(name, JobProfileType.PARALLEL_HOMOGENEOUS)
        self.__cpu = float(cpu)
        self.__com = float(com)

    @property
    def cpu(self) -> float:
        """The amount of flop/s to be computed on each host."""
        return self.__cpu

    @property
    def com(self) -> float:
        """The amount of bytes to be transfered between hosts."""
        return self.__com


class ParallelHomogeneousTotalJobProfile(JobProfile):
    """ Batsim Parallel Homogeneous Total Job Profile class.

    This class describes a job that equally distributes the total
    amount of computation and communication between the allocated hosts.

    Args:
        name: The profile name. Must be unique within a workload.
        cpu: The total amount of flop/s to be computed over all hosts.
        com: The total amount of bytes to be sent and received on each
            pair of hosts.

    Raises:
        TypeError: In case of invalid arguments.

    Examples:
        >>> profile = ParallelHomogeneousTotalJobProfile("name", cpu=10e6, com=5e6)
    """

    def __init__(self, name: str, cpu:  Union[int, float], com:  Union[int, float]) -> None:
        super().__init__(name, JobProfileType.PARALLEL_HOMOGENEOUS_TOTAL)
        self.__cpu = float(cpu)
        self.__com = float(com)

    @property
    def cpu(self) -> float:
        """The total amount of flop/s to be computed."""
        return self.__cpu

    @property
    def com(self) -> float:
        """The total amount of bytes to be sent and received."""
        return self.__com


class ComposedJobProfile(JobProfile):
    """ Batsim Composed Job Profile class.

    This class describes a job that executes a sequence of profiles.

    Args:
        name: The profile name. Must be unique within a workload.
        profiles: The profiles to execute.
        repeat: The number of times to repeat the sequence.

    Raises:
        TypeError: In case of invalid arguments.
        ValueError: In case of `repeat` argument is less than 1.

    Examples:
        >>> profile_1 = ParallelHomogeneousTotalJobProfile("prof1", cpu=10e6, com=5e6)
        >>> profile_2 = ParallelHomogeneousTotalJobProfile("prof2", cpu=1e6, com=2e6)
        >>> composed = ComposedJobProfile("composed", profiles=[profile_1, profile_2], repeat=2)
    """

    def __init__(self, name: str, profiles: Sequence[JobProfile], repeat: int = 1) -> None:
        super().__init__(name, JobProfileType.COMPOSED)
        if repeat <= 0:
            raise ValueError('Expected `repeat` argument to be greater'
                             'than 0, got {}'.format(repeat))
        if not all(isinstance(p, JobProfile) for p in profiles):
            raise TypeError('Expected `profiles` argument to be a '
                            'sequence of `JobProfile`, got {}'.format(profiles))

        self.__repeat = int(repeat)
        self.__profiles = list(profiles)

    @property
    def repeat(self) -> int:
        """The number of times that the profile sequence will repeat."""
        return self.__repeat

    @property
    def profiles(self) -> Sequence[JobProfile]:
        """The sequence of profiles to execute."""
        return self.__profiles


class ParallelHomogeneousPFSJobProfile(JobProfile):
    """ Batsim Homogeneous Job with IO to/from PFS Profile class.

    This class describes a job that represents an IO transfer between
    the allocated hosts and a storage resource. 

    Args:
        name: The profile name. Must be unique within a workload.
        bytes_to_read: The amount of bytes to read.
        bytes_to_write: The amount of bytes to write.
        storage: The storage resource label.

    Raises:
        TypeError: In case of invalid arguments.
        ValueError: In case of `bytes_to_read` and `bytes_to_write` arguments
            are not greater than or equal to zero and `storage` argument is 
            not a valid string.

    Examples:
        >>> pfs = ParallelHomogeneousPFSJobProfile("pfs", bytes_to_read=10e6, bytes_to_write=1e6, storage="pfs")
    """

    def __init__(self,
                 name: str,
                 bytes_to_read: Union[int, float],
                 bytes_to_write: Union[int, float],
                 storage: str = 'pfs') -> None:
        super().__init__(name, JobProfileType.PARALLEL_HOMOGENEOUS_PFS)

        if bytes_to_read < 0:
            raise ValueError('Expected `bytes_to_read` argument to be '
                             'a positive number, got {}'.format(bytes_to_read))
        if bytes_to_write < 0:
            raise ValueError('Expected `bytes_to_write` argument to be '
                             'a positive number, got {}'.format(bytes_to_write))
        if not storage:
            raise ValueError('Expected `storage` argument to be a '
                             'valid string, got {}'.format(storage))

        self.__bytes_to_read = float(bytes_to_read)
        self.__bytes_to_write = float(bytes_to_write)
        self.__storage = str(storage)

    @property
    def bytes_to_read(self) -> float:
        """ The amount of bytes to read. """
        return self.__bytes_to_read

    @property
    def bytes_to_write(self) -> float:
        """ The amount of bytes to write. """
        return self.__bytes_to_write

    @property
    def storage(self) -> str:
        """ The storage label """
        return self.__storage


class DataStagingJobProfile(JobProfile):
    """ Batsim Data Staging Job Profile class.

    This class describes a job that represents an IO transfer between
    two storage resources.

    Args:
        name: The profile name. Must be unique within a workload.
        nb_bytes: The amount of bytes to be transferred.
        src: The sending storage label (source).
        dest: The receiving storage label (destination).

    Raises:
        TypeError: In case of invalid arguments.
        ValueError: In case of `nb_bytes` argument is not greater than or equal 
            to zero and `src` and `dest` arguments are not valid strings.

    Examples:
        >>> data = DataStagingJobProfile("data", nb_bytes=10e6, src="pfs", dest="nfs")
    """

    def __init__(self, name: str, nb_bytes: Union[int, float], src: str, dest: str) -> None:
        super().__init__(name, JobProfileType.DATA_STAGING)

        if nb_bytes < 0:
            raise ValueError('Expected `nb_bytes` argument to be a '
                             'positive number, got {}'.format(nb_bytes))

        if not src:
            raise ValueError('Expected `src` argument to be a '
                             'valid string, got {}'.format(src))
        if not dest:
            raise ValueError('Expected `dest` argument to be a '
                             'valid string, got {}'.format(dest))

        self.__nb_bytes = float(nb_bytes)
        self.__src = str(src)
        self.__dest = str(dest)

    @property
    def dest(self) -> str:
        """ The receiving storage label."""
        return self.__dest

    @property
    def src(self) -> str:
        """ The sending storage label. """
        return self.__src

    @property
    def nb_bytes(self) -> float:
        """ The amount of bytes to be transferred. """
        return self.__nb_bytes


class Job(Identifier):
    """ Batsim Job class.

    This class describes a rigid job.

    Attributes:
        WORKLOAD_SEPARATOR: A char that separates the workload name from 
            the job name. By default Batsim submits the workload along with 
            the job name in the id field.

    Args:
        name: The job name. Must be unique within a workload.
        workload: The job workload name.
        res: The number of resources requested.
        profile: The job profile to be executed.
        subtime: The submission time.
        walltime: The execution time limit (maximum execution time).
        user: The job owner name.

    Raises:
        TypeError: In case of invalid arguments.
    """

    WORKLOAD_SEPARATOR: str = "!"

    def __init__(self,
                 name: str,
                 workload: str,
                 res: int,
                 profile: JobProfile,
                 subtime: Union[int, float],
                 walltime: Optional[Union[int, float]] = None,
                 user: Optional[str] = None) -> None:

        if not isinstance(profile, JobProfile):
            raise TypeError('Expected `profile` argument to be a '
                            'instance of JobProfile, got {}'.format(profile))

        job_id = "%s%s%s" % (str(workload), self.WORKLOAD_SEPARATOR, str(name))
        super().__init__(job_id)

        self.__res = int(res)
        self.__profile = profile
        self.__subtime = float(subtime)
        self.__walltime = walltime
        self.__user = user

        self.__state: JobState = JobState.UNKNOWN
        self.__allocation: Optional[Sequence[Union[int, str]]] = None
        self.__start_time: Optional[float] = None  # will be set on start
        self.__stop_time: Optional[float] = None  # will be set on terminate

    def __repr__(self):
        return "Job_%s" % self.id

    @property
    def name(self) -> str:
        """ The job name. """
        return self.id.split(self.WORKLOAD_SEPARATOR)[1]

    @property
    def workload(self) -> str:
        """ The job workload name. """
        return self.id.split(self.WORKLOAD_SEPARATOR)[0]

    @property
    def subtime(self) -> float:
        """ The job submission time. """
        return self.__subtime

    @property
    def res(self) -> int:
        """ The number of resources requested. """
        return self.__res

    @property
    def profile(self) -> JobProfile:
        """ The job profile. """
        return self.__profile

    @property
    def walltime(self) -> Optional[Union[int, float]]:
        """ The job maximum execution time. """
        return self.__walltime

    @property
    def user(self) -> Optional[str]:
        """ The job owner name. """
        return self.__user

    @property
    def state(self) -> JobState:
        """  The current job state. """
        return self.__state

    @property
    def allocation(self) -> Optional[Sequence[Union[str, int]]]:
        """ The allocated resources id. """
        return self.__allocation

    @property
    def is_running(self) -> bool:
        """ Whether this job is running or not. """
        return self.__state == JobState.RUNNING

    @property
    def is_runnable(self) -> bool:
        """ Whether this job is able to start. """
        return self.__state == JobState.ALLOCATED

    @property
    def is_submitted(self) -> bool:
        """ Whether this job was submitted. """
        return self.__state == JobState.SUBMITTED

    @property
    def is_finished(self) -> bool:
        """ Whether this job finished. """
        return self.stop_time is not None

    @property
    def start_time(self) -> Optional[float]:
        """ The job start time. """
        return self.__start_time

    @property
    def stop_time(self) -> Optional[float]:
        """ The job stop time. """
        return self.__stop_time

    @property
    def dependencies(self) -> Optional[Sequence[str]]:
        """ The id of the jobs it depends. """
        return None

    @property
    def waiting_time(self) -> Optional[float]:
        """ The job waiting time. """
        if self.start_time is None:
            return None
        else:
            return self.start_time - self.subtime

    @property
    def runtime(self) -> Optional[float]:
        """ The job runtime. """
        if self.stop_time is None or self.start_time is None:
            return None
        else:
            return self.stop_time - self.start_time

    @property
    def stretch(self) -> Optional[float]:
        """ The job stretch. """
        stretch = None
        if self.waiting_time is not None:
            if self.walltime is not None:
                stretch = self.waiting_time / self.walltime
            elif self.runtime is not None:
                stretch = self.waiting_time / self.runtime
        return stretch

    @property
    def turnaround_time(self) -> Optional[float]:
        """ The job turnaround time. """
        if self.waiting_time is None or self.runtime is None:
            return None
        else:
            return self.waiting_time + self.runtime

    @property
    def per_processor_slowdown(self) -> Optional[float]:
        """ The job per-processor slowdown. """
        if self.turnaround_time is None or self.runtime is None:
            return None
        else:
            return max(1., self.turnaround_time / (self.res * self.runtime))

    @property
    def slowdown(self) -> Optional[float]:
        """ The job slowdown. """
        if self.turnaround_time is None or self.runtime is None:
            return None
        else:
            return max(1., self.turnaround_time / self.runtime)

    def _allocate(self, hosts: Sequence[Union[int, str]]):
        """ Allocate hosts for the job. 

        This is an internal method to be used by the simulator only.

        Args:
            hosts: A sequence containing the allocated hosts ids.

        Raises:
            RuntimeError: In case of the job is already allocated or 
                the number of resources does not match the request.

        Dispatch:
            Event: JobEvent.ALLOCATED
        """
        if self.__allocation is not None:
            raise RuntimeError('This job was already allocated.'
                               'got, {}'.format(self.state))
        if len(hosts) != self.res:
            raise RuntimeError('Expected `hosts` argument to be a list of hosts '
                               'of lenght {}, got {}'.format(self.res, hosts))

        self.__allocation = list(hosts)
        self.__state = JobState.ALLOCATED
        self.__dispatch(JobEvent.ALLOCATED)

    def _reject(self):
        """ Reject the job. 

        This is an internal method to be used by the simulator only.

        Dispatch:
            Event: JobEvent.REJECTED
        """
        self.__state == JobState.REJECTED
        self.__dispatch(JobEvent.REJECTED)

    def _submit(self, subtime: Union[int, float]):
        """ Submit the job. 

        This is an internal method to be used by the simulator only.

        Args:
            subtime: The submission time.

        Raises:
            RuntimeError: In case of the job was already submitted or 
                the subtime is less than zero.

        Dispatch:
            Event: JobEvent.SUBMITTED
        """
        if self.state != JobState.UNKNOWN:
            raise RuntimeError('This job was already submitted.'
                               'got, {}'.format(self.state))
        if subtime < 0:
            raise RuntimeError('Expected `subtime` argument to be greather '
                               'than zero, got {}'.format(subtime))

        self.__state = JobState.SUBMITTED
        self.__subtime = float(subtime)
        self.__dispatch(JobEvent.SUBMITTED)

    def _kill(self, current_time: Union[int, float]):
        """ Kill the job. 

        This is an internal method to be used by the simulator only.

        Args:
            current_time: The current simulation time.

        Raises:
            RuntimeError: In case of the job is not running or 
                the current time is less than the job start time.

        Dispatch:
            Event: JobEvent.KILLED
        """
        if self.start_time is None:
            raise RuntimeError('The job cannot be killed if it is not running'
                               'got, {}'.format(self.state))

        if current_time < self.start_time:
            raise RuntimeError('Expected `current_time` argument to be greather '
                               'than start_time, got {}'.format(current_time))

        self.__stop_time = float(current_time)
        self.__state = JobState.COMPLETED_KILLED
        self.__dispatch(JobEvent.KILLED)

    def _start(self, current_time: Union[int, float]):
        """ Start the job. 

        This is an internal method to be used by the simulator only.

        Args:
            current_time: The current simulation time.

        Raises:
            RuntimeError: In case of the job is was already started or 
                the job is not runnable or the current time is less than
                the job submission time.

        Dispatch:
            Event: JobEvent.STARTED
        """
        if self.start_time is not None:
            raise RuntimeError('The job was already started '
                               'at {}'.format(self.start_time))
        if not self.is_runnable:
            raise RuntimeError('The job cannot start if it is not '
                               'runnable, got {}'.format(self.state))

        if current_time < self.subtime:
            raise RuntimeError('The `current_time` argument cannot be less '
                               'than the job submission time, '
                               'got {}'.format(current_time))

        self.__start_time = float(current_time)
        self.__state = JobState.RUNNING
        self.__dispatch(JobEvent.STARTED)

    def _terminate(self, current_time: Union[int, float], state: JobState):
        """ Terminate the job. 

        This is an internal method to be used by the simulator only.

        Args:
            current_time: The current simulation time.
            state: The last state of the job.

        Raises:
            RuntimeError: In case of the job is not running or 
                the current time is less than the job start time or 
                the state is not one of the possible ones.

        Dispatch:
            Event: JobEvent.COMPLETED

        """
        if self.start_time is None:
            raise RuntimeError('The job cannot be finished if it is not running'
                               'got, {}'.format(self.state))

        if not state in (JobState.COMPLETED_SUCCESSFULLY, JobState.COMPLETED_FAILED, JobState.COMPLETED_WALLTIME_REACHED):
            raise RuntimeError('Expected `state` argument to be one of '
                               '[SUCCESSFULLY, FAILED, WALLTIME_REACHED], '
                               'got {}'.format(state))

        if current_time < self.start_time:
            raise RuntimeError('Expected `current_time` argument to be greather '
                               'than start_time, got {}'.format(current_time))

        self.__stop_time = float(current_time)
        self.__state = state
        self.__dispatch(JobEvent.COMPLETED)

    def __dispatch(self, event_type: JobEvent):
        """ Dispatch job events and cleanup unnecessary connections. 


        It is not possible to occur two events of the same type in a single job. 
        Thus, when an event is dispatched it automatically disconnect all listeners. 
        This is an internal method to be used only by a job instance.

        Args:
            event_type: the event type to dispatch.

        Raises:
            AssertionError: In case of invalid arguments.
        """
        assert isinstance(event_type, JobEvent)

        # dispatch event
        dispatcher.send(signal=event_type, sender=self)

        # disconnect listeners
        listeners = dispatcher.getReceivers(self, event_type)
        for r in list(dispatcher.liveReceivers(listeners)):
            dispatcher.disconnect(r, signal=event_type, sender=self)
