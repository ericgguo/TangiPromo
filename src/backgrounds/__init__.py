from .aurora_flow import AuroraFlowBackground
from .particles import ParticleConstellationBackground
from .aurora import AuroraBackground
from .neon import NeonGlowBackground
from .geometric import GeometricBackground
from .waves import AbstractWavesBackground
from .custom import CustomCodeBackground

ALL_BACKGROUNDS: list = [
    AuroraFlowBackground,
    AuroraBackground,
    AbstractWavesBackground,
    NeonGlowBackground,
    GeometricBackground,
    ParticleConstellationBackground,
    CustomCodeBackground,
]

BACKGROUND_MAP: dict[str, type] = {cls().name: cls for cls in ALL_BACKGROUNDS}
