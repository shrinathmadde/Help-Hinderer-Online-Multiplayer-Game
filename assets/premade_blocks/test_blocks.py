from assets.premade_trials.index import namedPremadeIndex
from backend.block import Block
from backend.scoring import ConstantRewardCalculator
from backend.trial_provider import TrialProviderFromPremade

premade_test_blocks: list[Block] = [
    Block(
        blockDescriptor="Practice",
        instructions=[
            "Dies ist eine Übungsrunde. Du erhältst keine Punkte.",
            "Spieler 0 ist immer Rot. Spieler 1 ist immer Blau.",
            "Verwende die Pfeiltasten, um dich zu bewegen. Du kannst bis zu 2 Züge pro Runde machen.",
            "Drücke die Leertaste, um eine Box zu platzieren (falls erlaubt).",
            "Der Spieler mit dem Stern über sich kann das Ziel betreten.",
            "Der andere Spieler kann versuchen, eine Box in der Nähe zu bewegen oder zu platzieren (mit der Leertaste).",
            "Probiere Bewegung, das Erreichen des Sterns und das Platzieren einer Box aus, um dich mit der Steuerung vertraut zu machen."
        ],
        trialProvider=TrialProviderFromPremade(namedPremadeIndex["Practice"]),
        rewardCalculator=ConstantRewardCalculator(0, 0)
    ),
    Block(
        blockDescriptor="Hinderer",
        instructions=[
            "Spieler 0 ist immer Rot. Spieler 1 ist immer Blau.",
            "Der Spieler mit dem Stern über sich kann das Ziel betreten.",
            "Der andere Spieler kann versuchen, mit der Leertaste eine Box zu platzieren oder zu bewegen, um den Spieler mit dem Stern zu blockieren.",
            "Dein Ziel ist es, entweder den Stern zu erreichen (wenn du ihn hast) oder den anderen Spieler zu verlangsamen (wenn du ihn nicht hast).",
            "Belohnung: Der Spieler, der den Stern erreicht, erhält die gesamte Belohnung."
        ],
        trialProvider=TrialProviderFromPremade(namedPremadeIndex["Hinderer"]),
        rewardCalculator=ConstantRewardCalculator(0, 1)
    ),
    Block(
        blockDescriptor="Helper",
        instructions=[
            "Spieler 0 ist immer Rot. Spieler 1 ist immer Blau.",
            "Der Spieler mit dem Stern über sich kann das Ziel betreten.",
            "Der andere Spieler kann versuchen, mit der Leertaste eine nahegelegene Box zu bewegen oder zu entfernen, um dem Spieler mit dem Stern zu helfen, das Ziel zu erreichen.",
            "Dein Ziel ist es, entweder den Stern zu erreichen (wenn du ihn hast) oder dem anderen Spieler zu helfen.",
            "Belohnung: Wenn der Spieler mit dem Stern das Ziel erreicht, wird die Belohnung zwischen beiden Spielern aufgeteilt."
        ],
        trialProvider=TrialProviderFromPremade(namedPremadeIndex["Helper"]),
        rewardCalculator=ConstantRewardCalculator(0, 1)
    ),
    Block(
        blockDescriptor="Unknown",
        instructions=[
            "Spieler 0 ist immer Rot. Spieler 1 ist immer Blau.",
            "Der Spieler mit dem Stern über sich kann das Ziel betreten.",
            "Der andere Spieler kann entscheiden, ob er hilft oder hindert, indem er mit der Leertaste eine Box bewegt oder platziert.",
            "Dein Ziel hängt davon ab, ob du helfen oder blockieren möchtest.",
            "Belohnung: Manchmal wird die Belohnung geteilt. In anderen Fällen erhält nur der Spieler, der den Stern erreicht, die Belohnung."
        ],
        trialProvider=TrialProviderFromPremade(namedPremadeIndex["Unknown"]),
        rewardCalculator=ConstantRewardCalculator(0, 1)
    )
]
