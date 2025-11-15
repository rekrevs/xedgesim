#!/usr/bin/env python3
"""
service_wrapper.py - Generic service wrapper for protocol adapter

This allows the container to be started with 'python -m service' as expected
by DockerProtocolAdapter, while actually running the echo service.
"""

if __name__ == "__main__":
    from containers.examples.echo_service import main
    main()
