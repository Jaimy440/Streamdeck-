"""Le Mans Ultimate Telemetrie über das rFactor-2-Shared-Memory-Plugin.

LMU basiert auf der rFactor-2-Engine und liefert seine Daten über das Plugin
"rFactor2SharedMemoryMapPlugin64.dll" (das auch CrewChief, SimHub & Co. nutzen).
Die Strukturen hier spiegeln rF2State.h (The Iron Wolf) 1:1 wieder – Reihenfolge,
Typen und Packing (4 Byte) müssen exakt stimmen.

read() liefert ein normalisiertes "Frame" (dict), das auch der Demo-Modus erzeugt.
"""
from __future__ import annotations

import ctypes
import math
import sys

MAX_VEHICLES = 128

c_long = ctypes.c_int32       # 'long' ist unter Windows 32 Bit
c_ulong = ctypes.c_uint32
c_bool = ctypes.c_bool
c_uchar = ctypes.c_ubyte
c_schar = ctypes.c_byte
c_double = ctypes.c_double
c_float = ctypes.c_float


class Vec3(ctypes.Structure):
    _pack_ = 4
    _fields_ = [("x", c_double), ("y", c_double), ("z", c_double)]


class Wheel(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mSuspensionDeflection", c_double),
        ("mRideHeight", c_double),
        ("mSuspForce", c_double),
        ("mBrakeTemp", c_double),
        ("mBrakePressure", c_double),
        ("mRotation", c_double),
        ("mLateralPatchVel", c_double),
        ("mLongitudinalPatchVel", c_double),
        ("mLateralGroundVel", c_double),
        ("mLongitudinalGroundVel", c_double),
        ("mCamber", c_double),
        ("mLateralForce", c_double),
        ("mLongitudinalForce", c_double),
        ("mTireLoad", c_double),
        ("mGripFract", c_double),
        ("mPressure", c_double),
        ("mTemperature", c_double * 3),
        ("mWear", c_double),
        ("mTerrainName", ctypes.c_char * 16),
        ("mSurfaceType", c_uchar),
        ("mFlat", c_bool),
        ("mDetached", c_bool),
        ("mStaticUndeflectedRadius", c_uchar),
        ("mVerticalTireDeflection", c_double),
        ("mWheelYLocation", c_double),
        ("mToe", c_double),
        ("mTireCarcassTemperature", c_double),
        ("mTireInnerLayerTemperature", c_double * 3),
        ("mExpansion", c_uchar * 24),
    ]


class VehicleTelemetry(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mID", c_long),
        ("mDeltaTime", c_double),
        ("mElapsedTime", c_double),
        ("mLapNumber", c_long),
        ("mLapStartET", c_double),
        ("mVehicleName", ctypes.c_char * 64),
        ("mTrackName", ctypes.c_char * 64),
        ("mPos", Vec3),
        ("mLocalVel", Vec3),
        ("mLocalAccel", Vec3),
        ("mOri", Vec3 * 3),
        ("mLocalRot", Vec3),
        ("mLocalRotAccel", Vec3),
        ("mGear", c_long),
        ("mEngineRPM", c_double),
        ("mEngineWaterTemp", c_double),
        ("mEngineOilTemp", c_double),
        ("mClutchRPM", c_double),
        ("mUnfilteredThrottle", c_double),
        ("mUnfilteredBrake", c_double),
        ("mUnfilteredSteering", c_double),
        ("mUnfilteredClutch", c_double),
        ("mFilteredThrottle", c_double),
        ("mFilteredBrake", c_double),
        ("mFilteredSteering", c_double),
        ("mFilteredClutch", c_double),
        ("mSteeringShaftTorque", c_double),
        ("mFront3rdDeflection", c_double),
        ("mRear3rdDeflection", c_double),
        ("mFrontWingHeight", c_double),
        ("mFrontRideHeight", c_double),
        ("mRearRideHeight", c_double),
        ("mDrag", c_double),
        ("mFrontDownforce", c_double),
        ("mRearDownforce", c_double),
        ("mFuel", c_double),
        ("mEngineMaxRPM", c_double),
        ("mScheduledStops", c_uchar),
        ("mOverheating", c_bool),
        ("mDetached", c_bool),
        ("mHeadlights", c_bool),
        ("mDentSeverity", c_uchar * 8),
        ("mLastImpactET", c_double),
        ("mLastImpactMagnitude", c_double),
        ("mLastImpactPos", Vec3),
        ("mEngineTorque", c_double),
        ("mCurrentSector", c_long),
        ("mSpeedLimiter", c_uchar),
        ("mMaxGears", c_uchar),
        ("mFrontTireCompoundIndex", c_uchar),
        ("mRearTireCompoundIndex", c_uchar),
        ("mFuelCapacity", c_double),
        ("mFrontFlapActivated", c_uchar),
        ("mRearFlapActivated", c_uchar),
        ("mRearFlapLegalStatus", c_uchar),
        ("mIgnitionStarter", c_uchar),
        ("mFrontTireCompoundName", ctypes.c_char * 18),
        ("mRearTireCompoundName", ctypes.c_char * 18),
        ("mSpeedLimiterAvailable", c_uchar),
        ("mAntiStallActivated", c_uchar),
        ("mUnused", c_uchar * 2),
        ("mVisualSteeringWheelRange", c_float),
        ("mRearBrakeBias", c_double),
        ("mTurboBoostPressure", c_double),
        ("mPhysicsToGraphicsOffset", c_float * 3),
        ("mPhysicalSteeringWheelRange", c_float),
        ("mBatteryChargeFraction", c_double),
        ("mElectricBoostMotorTorque", c_double),
        ("mElectricBoostMotorRPM", c_double),
        ("mElectricBoostMotorTemperature", c_double),
        ("mElectricBoostWaterTemperature", c_double),
        ("mElectricBoostMotorState", c_uchar),
        ("mExpansion", c_uchar * 111),
        ("mWheels", Wheel * 4),
    ]


class ScoringInfo(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mTrackName", ctypes.c_char * 64),
        ("mSession", c_long),
        ("mCurrentET", c_double),
        ("mEndET", c_double),
        ("mMaxLaps", c_long),
        ("mLapDist", c_double),
        ("pointer1", c_uchar * 8),
        ("mNumVehicles", c_long),
        ("mGamePhase", c_uchar),
        ("mYellowFlagState", c_schar),
        ("mSectorFlag", c_schar * 3),
        ("mStartLight", c_uchar),
        ("mNumRedLights", c_uchar),
        ("mInRealtime", c_bool),
        ("mPlayerName", ctypes.c_char * 32),
        ("mPlrFileName", ctypes.c_char * 64),
        ("mDarkCloud", c_double),
        ("mRaining", c_double),
        ("mAmbientTemp", c_double),
        ("mTrackTemp", c_double),
        ("mWind", Vec3),
        ("mMinPathWetness", c_double),
        ("mMaxPathWetness", c_double),
        ("mGameMode", c_uchar),
        ("mIsPasswordProtected", c_bool),
        ("mServerPort", ctypes.c_ushort),
        ("mServerPublicIP", c_ulong),
        ("mMaxPlayers", c_long),
        ("mServerName", ctypes.c_char * 32),
        ("mStartET", c_float),
        ("mAvgPathWetness", c_double),
        ("mExpansion", c_uchar * 200),
        ("pointer2", c_uchar * 8),
    ]


class VehicleScoring(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mID", c_long),
        ("mDriverName", ctypes.c_char * 32),
        ("mVehicleName", ctypes.c_char * 64),
        ("mTotalLaps", ctypes.c_short),
        ("mSector", c_schar),
        ("mFinishStatus", c_schar),
        ("mLapDist", c_double),
        ("mPathLateral", c_double),
        ("mTrackEdge", c_double),
        ("mBestSector1", c_double),
        ("mBestSector2", c_double),
        ("mBestLapTime", c_double),
        ("mLastSector1", c_double),
        ("mLastSector2", c_double),
        ("mLastLapTime", c_double),
        ("mCurSector1", c_double),
        ("mCurSector2", c_double),
        ("mNumPitstops", ctypes.c_short),
        ("mNumPenalties", ctypes.c_short),
        ("mIsPlayer", c_bool),
        ("mControl", c_schar),
        ("mInPits", c_bool),
        ("mPlace", c_uchar),
        ("mVehicleClass", ctypes.c_char * 32),
        ("mTimeBehindNext", c_double),
        ("mLapsBehindNext", c_long),
        ("mTimeBehindLeader", c_double),
        ("mLapsBehindLeader", c_long),
        ("mLapStartET", c_double),
        ("mPos", Vec3),
        ("mLocalVel", Vec3),
        ("mLocalAccel", Vec3),
        ("mOri", Vec3 * 3),
        ("mLocalRot", Vec3),
        ("mLocalRotAccel", Vec3),
        ("mHeadlights", c_uchar),
        ("mPitState", c_uchar),
        ("mServerScored", c_uchar),
        ("mIndividualPhase", c_uchar),
        ("mQualification", c_long),
        ("mTimeIntoLap", c_double),
        ("mEstimatedLapTime", c_double),
        ("mPitGroup", ctypes.c_char * 24),
        ("mFlag", c_uchar),
        ("mUnderYellow", c_bool),
        ("mCountLapFlag", c_uchar),
        ("mInGarageStall", c_bool),
        ("mUpgradePack", c_uchar * 16),
        ("mPitLapDist", c_float),
        ("mBestLapSector1", c_float),
        ("mBestLapSector2", c_float),
        ("mExpansion", c_uchar * 48),
    ]


class Telemetry(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mVersionUpdateBegin", c_ulong),
        ("mVersionUpdateEnd", c_ulong),
        ("mBytesUpdatedHint", ctypes.c_int32),
        ("mNumVehicles", c_long),
        ("mVehicles", VehicleTelemetry * MAX_VEHICLES),
    ]


class Scoring(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("mVersionUpdateBegin", c_ulong),
        ("mVersionUpdateEnd", c_ulong),
        ("mBytesUpdatedHint", ctypes.c_int32),
        ("mScoringInfo", ScoringInfo),
        ("mVehicles", VehicleScoring * MAX_VEHICLES),
    ]


TELEMETRY_MAP = "$rFactor2SMMP_Telemetry$"
SCORING_MAP = "$rFactor2SMMP_Scoring$"

SESSION_NAMES = {0: "Testtag"}
for _i in range(1, 5):
    SESSION_NAMES[_i] = "Training"
for _i in range(5, 9):
    SESSION_NAMES[_i] = "Qualifying"
SESSION_NAMES[9] = "Warm-up"
for _i in range(10, 14):
    SESSION_NAMES[_i] = "Rennen"


def session_kind(session: int) -> str:
    if 10 <= session <= 13:
        return "race"
    if 5 <= session <= 8:
        return "qualify"
    return "practice"


def _s(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("cp1252", errors="replace").strip()


def _k2c(k: float) -> float:
    return k - 273.15


# --------------------------------------------------------------------------------------
class SharedMemoryReader:
    """Liest Telemetrie + Scoring aus dem Shared Memory (nur Windows)."""

    def __init__(self):
        self._tel_map = None
        self._sco_map = None
        self.available = sys.platform == "win32"

    def _open(self) -> bool:
        if not self.available:
            return False
        if self._tel_map is None:
            import mmap
            try:
                self._tel_map = mmap.mmap(-1, ctypes.sizeof(Telemetry), TELEMETRY_MAP)
                self._sco_map = mmap.mmap(-1, ctypes.sizeof(Scoring), SCORING_MAP)
            except Exception:
                self._tel_map = self._sco_map = None
                return False
        return True

    @staticmethod
    def _consistent(cls, mm):
        """Kopie ziehen, bis Anfangs- und Endversion übereinstimmen (kein halber Frame)."""
        obj = None
        for _ in range(4):
            obj = cls.from_buffer_copy(mm)
            if obj.mVersionUpdateBegin == obj.mVersionUpdateEnd:
                return obj
        return obj

    def close(self):
        for m in (self._tel_map, self._sco_map):
            try:
                if m is not None:
                    m.close()
            except Exception:
                pass
        self._tel_map = self._sco_map = None

    def read(self) -> dict | None:
        if not self._open():
            return None
        try:
            sco = self._consistent(Scoring, self._sco_map)
            tel = self._consistent(Telemetry, self._tel_map)
        except Exception:
            return None
        info = sco.mScoringInfo
        n = max(0, min(info.mNumVehicles, MAX_VEHICLES))
        if sco.mVersionUpdateEnd == 0 or n == 0:
            return None
        return build_frame(info, sco.mVehicles, n, tel)


def build_frame(info: ScoringInfo, vehicles, n: int, tel: Telemetry) -> dict | None:
    # Telemetrie nach Slot-ID zuordnen
    tel_by_id = {}
    for i in range(max(0, min(tel.mNumVehicles, MAX_VEHICLES))):
        t = tel.mVehicles[i]
        tel_by_id[t.mID] = t

    cars = []
    player_scoring = None
    for i in range(n):
        v = vehicles[i]
        vel = v.mLocalVel
        car = {
            "id": v.mID,
            "driver": _s(v.mDriverName),
            "vehicle": _s(v.mVehicleName),
            "cls": _s(v.mVehicleClass),
            "place": v.mPlace,
            "laps": v.mTotalLaps,
            "lap_dist": v.mLapDist,
            "path_lateral": v.mPathLateral,
            "sector": {0: 3, 1: 1, 2: 2}.get(v.mSector, 1),
            "best": v.mBestLapTime if v.mBestLapTime > 0 else None,
            "last": v.mLastLapTime if v.mLastLapTime > 0 else None,
            "best_s1": v.mBestSector1 if v.mBestSector1 > 0 else None,
            "best_s2": (v.mBestSector2 - v.mBestSector1) if v.mBestSector2 > 0 and v.mBestSector1 > 0 else None,
            "last_s1": v.mLastSector1 if v.mLastSector1 > 0 else None,
            "last_s2": (v.mLastSector2 - v.mLastSector1) if v.mLastSector2 > 0 and v.mLastSector1 > 0 else None,
            "cur_s1": v.mCurSector1 if v.mCurSector1 > 0 else None,
            "cur_s2": (v.mCurSector2 - v.mCurSector1) if v.mCurSector2 > 0 and v.mCurSector1 > 0 else None,
            "pitstops": v.mNumPitstops,
            "penalties": v.mNumPenalties,
            "is_player": bool(v.mIsPlayer),
            "in_pits": bool(v.mInPits),
            "pit_state": v.mPitState,
            "time_behind_next": v.mTimeBehindNext,
            "laps_behind_next": v.mLapsBehindNext,
            "time_behind_leader": v.mTimeBehindLeader,
            "laps_behind_leader": v.mLapsBehindLeader,
            "lap_start_et": v.mLapStartET,
            "time_into_lap": v.mTimeIntoLap,
            "est_lap": v.mEstimatedLapTime,
            "pos": (v.mPos.x, v.mPos.y, v.mPos.z),
            "speed": math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2) * 3.6,
            "flag": v.mFlag,               # 0 = grün, 6 = blau
            "finish_status": v.mFinishStatus,
            "under_yellow": bool(v.mUnderYellow),
            "control": v.mControl,
        }
        if car["is_player"]:
            player_scoring = car
        cars.append(car)

    if player_scoring is None:
        return None

    session = info.mSession
    end_et = info.mEndET
    time_left = (end_et - info.mCurrentET) if end_et > 0 and end_et < 1e8 else None
    max_laps = info.mMaxLaps if 0 < info.mMaxLaps < 10000 else None

    frame = {
        "source": "lmu",
        "session": {
            "id": session,
            "name": SESSION_NAMES.get(session, "Session"),
            "kind": session_kind(session),
            "phase": info.mGamePhase,
            "elapsed": info.mCurrentET,
            "time_left": max(0.0, time_left) if time_left is not None else None,
            "max_laps": max_laps,
            "track": _s(info.mTrackName),
            "track_length": info.mLapDist,
            "yellow_state": info.mYellowFlagState,
            "sector_flags": [int(info.mSectorFlag[i]) for i in range(3)],
            "start_lights": info.mStartLight,
            "red_lights": info.mNumRedLights,
            "in_realtime": bool(info.mInRealtime),
            "raining": info.mRaining,
            "dark_cloud": info.mDarkCloud,
            "air_temp": info.mAmbientTemp,
            "track_temp": info.mTrackTemp,
            "wetness": info.mAvgPathWetness,
            "num_cars": n,
        },
        "cars": cars,
        "player": None,
    }

    t = tel_by_id.get(player_scoring["id"])
    if t is None:
        return frame

    vel = t.mLocalVel
    tyres = []
    for w in t.mWheels:
        tyres.append({
            "temps": [round(_k2c(w.mTemperature[j]), 1) for j in range(3)],
            "inner": [round(_k2c(w.mTireInnerLayerTemperature[j]), 1) for j in range(3)],
            "carcass": round(_k2c(w.mTireCarcassTemperature), 1),
            "pressure": round(w.mPressure, 1),
            "wear": max(0.0, min(1.0, w.mWear)),      # 1.0 = neu
            "flat": bool(w.mFlat),
            "detached": bool(w.mDetached),
            "brake_temp": round(_k2c(w.mBrakeTemp), 0),
            "surface": w.mSurfaceType,
        })
    sector_raw = t.mCurrentSector
    frame["player"] = {
        "vehicle": _s(t.mVehicleName),
        "speed": math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2) * 3.6,
        "gear": t.mGear,
        "rpm": t.mEngineRPM,
        "max_rpm": t.mEngineMaxRPM,
        "throttle": t.mFilteredThrottle,
        "brake": t.mFilteredBrake,
        "clutch": t.mFilteredClutch,
        "steering": t.mFilteredSteering,
        "fuel": t.mFuel,
        "fuel_capacity": t.mFuelCapacity,
        "lap_number": t.mLapNumber,
        "lap_start_et": t.mLapStartET,
        "elapsed": t.mElapsedTime,
        "water_temp": t.mEngineWaterTemp,
        "oil_temp": t.mEngineOilTemp,
        "overheating": bool(t.mOverheating),
        "detached": bool(t.mDetached),
        "dents": [int(x) for x in t.mDentSeverity],
        "last_impact_et": t.mLastImpactET,
        "last_impact_mag": t.mLastImpactMagnitude,
        "limiter": bool(t.mSpeedLimiter),
        "in_pitlane": sector_raw < 0,      # Vorzeichen-Bit = Boxengasse
        "headlights": bool(t.mHeadlights),
        "rear_brake_bias": t.mRearBrakeBias,
        "battery": t.mBatteryChargeFraction if t.mElectricBoostMotorState > 0 else None,
        "boost_state": t.mElectricBoostMotorState,
        "tyres": tyres,
        "compound_front": _s(t.mFrontTireCompoundName),
        "compound_rear": _s(t.mRearTireCompoundName),
        "pos": (t.mPos.x, t.mPos.y, t.mPos.z),
        "ori_z": (t.mOri[0].z, t.mOri[1].z, t.mOri[2].z),   # Spalte "lokales z" in Weltkoordinaten
        "ori_x": (t.mOri[0].x, t.mOri[1].x, t.mOri[2].x),   # Spalte "lokales x" in Weltkoordinaten
        "virtual_energy": None,          # kommt ggf. über die LMU-REST-API
    }
    return frame
