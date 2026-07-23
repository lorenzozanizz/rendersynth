from ..utils.logger import UniqueLogger

from abc import abstractmethod, ABCMeta


class FrameContext:
    """Inner context: captures state at each frame, restores after render"""

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.frame_contexts = []

        self.from_pipeline(pipeline)

    def from_pipeline(self, pipeline) -> None:

        for pipe in pipeline:
            # Check for frame context (per-frame state)
            if hasattr(pipe, 'get_frame_context'):
                ctx = pipe.get_frame_context()
                # Some pipes in the scene may not require per-frame restoring, e.g.
                # pipes which do not do offset
                if ctx is not None:
                    self.frame_contexts.append(ctx)


    def __enter__(self):
        for ctx in self.frame_contexts:
            ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for ctx in reversed(self.frame_contexts):
            try:
                ctx.__exit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                UniqueLogger.quick_log(f"Error exiting frame context: {e}")
        return False


class NestedPipelineContext:
    """Outer context: captures global state, releases at the very end"""

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.global_contexts = []

        self.from_pipeline(pipeline)

        self._frame_context = FrameContext(pipeline)

    def from_pipeline(self, pipeline) -> None:
        for pipe in pipeline:
            if hasattr(pipe, 'get_global_context'):
                ctx = pipe.get_global_context()
                # Some pipes in the scene may not edit anything requiring restoring.
                if ctx is not None:
                    self.global_contexts.append(ctx)

    def frame_context(self) -> FrameContext:
        """Return a context manager for each frame"""
        return self._frame_context

    def __enter__(self):

        for ctx in self.global_contexts:
            ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Exit global contexts (outermost level)
        for ctx in reversed(self.global_contexts):
            try:
                ctx.__exit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                UniqueLogger.quick_log(f"Error exiting global context: {e}")
        return False


class DoubleFramedPipe(metaclass=ABCMeta):

    @abstractmethod
    def get_global_context(self):
        pass

    @abstractmethod
    def get_frame_context(self):
        pass


class ContextManager:
    """Restore scales after each frame"""

    def __enter__(self) -> 'ContextManager':
        pass

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        pass
