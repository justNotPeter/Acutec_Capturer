from robodk import robolink
from robodk import robomath as rm

RDK = robolink.Robolink()
robot = RDK.Item('Fanuc CRX-10iA/L')
robot.MoveJ([0, -30, 0, 0, 90, 180])