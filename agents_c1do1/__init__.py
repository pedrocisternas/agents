"""
C1DO1 Agents Package

This package contains the implementation of the C1DO1 agent system
following the OpenAI Agents SDK best practices.
"""

# Import the main agents for easier access
from agents_c1do1.simple_response_agent import simple_response_agent
from agents_c1do1.complex_response_agent import complex_response_agent
from agents_c1do1.human_support_agent import human_support_agent

__all__ = [
    "simple_response_agent",
    "complex_response_agent",
    "human_support_agent"
]