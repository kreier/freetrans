"""Base provider interface for freetrans."""

import abc
import typing
from freetrans.models import Detected, Translated


class BaseProvider(abc.ABC):
    """Abstract base class for all free translation providers."""

    name: str = "base"

    def __init__(self, **kwargs: typing.Any):
        self.kwargs = kwargs

    @abc.abstractmethod
    async def translate(
        self,
        text: typing.Union[str, typing.List[str]],
        dest: str = "en",
        src: str = "auto",
        **kwargs: typing.Any,
    ) -> typing.Union[Translated, typing.List[Translated]]:
        """Translate text(s) asynchronously."""
        pass

    @abc.abstractmethod
    async def detect(
        self,
        text: typing.Union[str, typing.List[str]],
        **kwargs: typing.Any,
    ) -> typing.Union[Detected, typing.List[Detected]]:
        """Detect language asynchronously."""
        pass

    @abc.abstractmethod
    async def aclose(self) -> None:
        """Close provider resources."""
        pass
