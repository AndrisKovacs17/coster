"""Forecast ladder: persistence, flow balance with the allocation cascade, then
learned corrections only once there is enough history. A rung stays only if
it beats the simpler one on the alerts it gives, not only on average error.
"""
