from bidict import frozenbidict

# TODO define exact triggers
# rough division of trigger numbers over 0-255
# 0 -> reset for gpio, no information
# 1-99 player0 specific probably dont need 100?
# 101-199 player1 specific
#   movement 4x, rejected?
#   collections
#   moving block?
#   ? inputs ?
# 200-255 game stuff
#   when enter engine state -> engine state changes logged during tick saving
#   trigger setup
triggers: frozenbidict[str, int] = frozenbidict(
    {
        "STARTEDTRIGGERSENDER": 255,
        "STARTEDTRIGGERSENDER_SEQBASE": 250,
        "TRIALRESULT_P0SCORED": 300,
        "TRIALRESULT_P1SCORED": 301,
        "TRIALRESULT_MAXTURNSREACHED": 302,
        "TRIALRESULT_TIMEMAXREACHED": 303,
        "TRIALRESULT_PLAYERTRAPPED": 304,
        "TRIALRESULT_ERROR": 240,
        "NEWTRIALLOADED": 200,
    }
)
