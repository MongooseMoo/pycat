import typing

from .mongoose import Mongoose


class Localgoose(Mongoose):
    def getHostPort(self) -> tuple[str, int]:
        return "localhost", 7777


def getClass() -> typing.Any:
    return Localgoose
