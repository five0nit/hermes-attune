"""Native checkout loader; wheel entry point loads hermes_attune instead."""
if __package__:
    from .hermes_attune import register
else:  # pytest imports a hyphenated checkout's root as a top-level module.
    from hermes_attune import register
