screenDefaultX = 1920
screenDefaultY = 1080

# screen id, isFlipped, (xSize, ySize)
multiscreen_default = [
    (0, False, (screenDefaultX, screenDefaultY)),
    (1, False, (screenDefaultX, screenDefaultY)),
    (2, True, (screenDefaultX, screenDefaultY)),
]

# only square supported
gameArea_xDim = 300
gameArea_yDim = gameArea_xDim

gameArea_xOffset = int((screenDefaultX - gameArea_xDim) / 2) - 200
gameArea_yOffset = int((screenDefaultY - gameArea_yDim) / 2) - 200


windowColor = (-1, -1, -1)

gridColor = (1, 1, 1)
gridWidth = 1

wallColor = (1, 1, 1)
wallWidth = 5

disabledColor = (1, 1, 1)
disabledWidth = 2

movableBoxColor = (1, 1, 1)

targetColor = (1, 0.82745098, -1)

p0Color = (1, -1, -1)

p1Color = (-1, -1, 1)

playerTurnIndicatorColor = (1, 1, 1)

resultTextXOffset = 200
resultTextYOffset = 200

resultTextSize = 250
