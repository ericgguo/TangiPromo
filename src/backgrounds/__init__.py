from .gradient import MeshGradientBackground
from .particles import ParticleConstellationBackground
from .aurora import AuroraBackground
from .neon import NeonGlowBackground
from .geometric import GeometricBackground
from .waves import AbstractWavesBackground
from .custom import CustomCodeBackground

ALL_BACKGROUNDS: list = [
    MeshGradientBackground,
    AbstractWavesBackground,
    AuroraBackground,
    NeonGlowBackground,
    GeometricBackground,
    ParticleConstellationBackground,
    CustomCodeBackground,
]

BACKGROUND_MAP: dict[str, type] = {cls().name: cls for cls in ALL_BACKGROUNDS}
