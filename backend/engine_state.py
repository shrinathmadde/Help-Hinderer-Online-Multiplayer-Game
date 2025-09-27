from enum import Enum


class EngineState(Enum):
    """states engine can be in

    0 - 99 engine/block states \n
    100 - 199 trial states
    """

    ENGINESTART = 0
    GETNEXTBLOCK = 10
    BLOCKSTART = 20
    BLOCKINSTRUCTIONS = 21
    BLOCKEND = 40
    ENGINEEND = 99
    TRIALNOTSTARTED = 100
    WAITSTART = 101
    P0TURN = 102
    P1TURN = 103
    LOADTRIALUI = 104
    RESULT = 109
    ENDED = 110
    FINISHED = 199

    PAUSED = 300
    INVALIDGAMESTATE = 400
    ENGINECRASH = 500


def isEngineStateTransitionAllowed(
    oldState: EngineState, newState: EngineState
) -> bool:
    allowed = False
    match oldState:
        case EngineState.ENGINESTART:
            if newState in [EngineState.GETNEXTBLOCK]:
                allowed = True
        case EngineState.GETNEXTBLOCK:
            if newState in [EngineState.BLOCKSTART, EngineState.ENGINEEND]:
                allowed = True
        case EngineState.BLOCKSTART:
            if newState in [EngineState.BLOCKINSTRUCTIONS]:
                allowed = True
        case EngineState.BLOCKINSTRUCTIONS:
            if newState in [EngineState.TRIALNOTSTARTED]:
                allowed = True
        case EngineState.TRIALNOTSTARTED:
            if newState in [
                EngineState.LOADTRIALUI,
                EngineState.INVALIDGAMESTATE,
                EngineState.FINISHED,
            ]:
                allowed = True
        case EngineState.LOADTRIALUI:
            if newState in [EngineState.WAITSTART]:
                allowed = True
        case EngineState.WAITSTART:
            if newState in [EngineState.P0TURN, EngineState.P1TURN]:
                allowed = True
        case EngineState.P0TURN:
            if newState in [EngineState.P1TURN, EngineState.RESULT]:
                allowed = True
        case EngineState.P1TURN:
            if newState in [EngineState.P0TURN, EngineState.RESULT]:
                allowed = True
        case EngineState.RESULT:
            if newState in [EngineState.TRIALNOTSTARTED]:
                allowed = True
        case EngineState.FINISHED:
            if newState in [EngineState.BLOCKEND]:
                allowed = True
        case EngineState.BLOCKEND:
            if newState in [EngineState.GETNEXTBLOCK]:
                allowed = True
        case EngineState.INVALIDGAMESTATE:
            if newState in [EngineState.ENGINECRASH]:
                allowed = True
        case EngineState.ENGINECRASH:
            if newState in [EngineState.ENDED]:
                allowed = True
    return allowed
