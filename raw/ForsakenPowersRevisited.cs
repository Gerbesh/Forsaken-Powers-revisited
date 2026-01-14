﻿// ForsakenPowersPlusMod.cs
// BepInEx 5.x + Harmony
// Valheim: Forsaken powers QoL
// Features:
// - Cycle available Forsaken Powers (hotkey)
// - Reset cooldown (hotkey)
// - Alt mode: when activating power, also activates all unlocked powers at once (server-authoritative)
// - Server-side config lock without ServerSync
// Fixed: powers are available only after killing the corresponding boss (ZoneSystem global keys)

using System;
using System.Collections.Generic;
using System.Linq;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using UnityEngine;

namespace ForsakenPowersPlus
{
    [BepInPlugin(ModGuid, ModName, ModVersion)]
    public class ForsakenPowersPlusMod : BaseUnityPlugin
    {
        public const string ModGuid = "pavel.forsakenpowersplus";
        public const string ModName = "Forsaken Powers Plus";
        public const string ModVersion = "1.1.1";

        internal static ManualLogSource Log;

        private Harmony _harmony;

        internal static class Cfg
        {
            internal static ConfigEntry<bool> Debug;
            internal static ConfigEntry<KeyCode> CycleHotkey;
            internal static ConfigEntry<KeyCode> ResetHotkey;

            internal static ConfigEntry<bool> EnableResetRemoval;

            internal static ConfigEntry<float> BuffCooldownSeconds;
            internal static ConfigEntry<float> BuffDurationSeconds;

            internal static ConfigEntry<bool> PassiveMode;
            internal static ConfigEntry<bool> EnableAltAllAtOnce;
            internal static ConfigEntry<bool> LockConfigOnServer;

            internal static ConfigEntry<string> MsgPowerSelected;
            internal static ConfigEntry<string> MsgPowerReset;
            internal static ConfigEntry<string> MsgPowerReady;
            internal static ConfigEntry<string> MsgPowerLocked;   // new
            internal static ConfigEntry<string> MsgNoUnlocked;    // new

            internal static void Bind(ConfigFile cfg)
            {
                Debug = cfg.Bind("1 - Mod", "Debug", false, "Enable debug logging.");

                CycleHotkey = cfg.Bind("2 - Hotkeys", "CyclePowerHotkey", KeyCode.F7, "Cycle through unlocked Forsaken Powers.");
                ResetHotkey = cfg.Bind("2 - Hotkeys", "ResetCooldownHotkey", KeyCode.F8, "Reset Forsaken Power cooldown and optionally remove active GP_ status effects.");

                EnableResetRemoval = cfg.Bind("3 - Behavior", "ResetRemovesActivePowers", true, "If true, reset will remove active GP_ status effects. If false, only cooldown is reset.");

                BuffCooldownSeconds = cfg.Bind("4 - Buff Tuning", "GuardianBuffCooldownSeconds", 1200f, "Cooldown for guardian powers (seconds).");
                BuffDurationSeconds = cfg.Bind("4 - Buff Tuning", "GuardianBuffDurationSeconds", 300f, "Duration for guardian powers (seconds).");

                PassiveMode = cfg.Bind("5 - Modes", "PassiveMode", false, "If true, GP_ effects become passive (ttl=0, cooldown=0).");
                EnableAltAllAtOnce = cfg.Bind("5 - Modes", "EnableAltAllAtOnce", true, "If true, holding Alt while activating power will activate all unlocked powers at once.");

                LockConfigOnServer = cfg.Bind("6 - Server", "LockConfigOnServer", true, "If true (recommended), server config becomes authoritative and is pushed to clients.");

                MsgPowerSelected = cfg.Bind("7 - Messages", "PowerSelected", "Power Selected", "Message shown when a power is selected.");
                MsgPowerReset = cfg.Bind("7 - Messages", "PowerReset", "Forsaken Power Has Been Reset", "Message shown when power is reset.");
                MsgPowerReady = cfg.Bind("7 - Messages", "PowerReady", "Ready To Stack Another Power", "Message shown when cooldown is reset but active powers are kept.");
                MsgPowerLocked = cfg.Bind("7 - Messages", "PowerLocked", "Forsaken power is locked (boss not defeated yet).", "Message shown when trying to use locked power.");
                MsgNoUnlocked = cfg.Bind("7 - Messages", "NoUnlocked", "No unlocked Forsaken powers yet.", "Message shown when cycling but nothing is unlocked.");
            }
        }

        internal static class Effective
        {
            internal static bool Debug;
            internal static KeyCode CycleHotkey;
            internal static KeyCode ResetHotkey;

            internal static bool EnableResetRemoval;

            internal static float BuffCooldownSeconds;
            internal static float BuffDurationSeconds;

            internal static bool PassiveMode;
            internal static bool EnableAltAllAtOnce;
            internal static bool LockConfigOnServer;

            internal static string MsgPowerSelected;
            internal static string MsgPowerReset;
            internal static string MsgPowerReady;
            internal static string MsgPowerLocked;
            internal static string MsgNoUnlocked;

            internal static bool ReceivedFromServer;

            internal static void LoadFromLocal()
            {
                Debug = Cfg.Debug.Value;
                CycleHotkey = Cfg.CycleHotkey.Value;
                ResetHotkey = Cfg.ResetHotkey.Value;

                EnableResetRemoval = Cfg.EnableResetRemoval.Value;

                BuffCooldownSeconds = Cfg.BuffCooldownSeconds.Value;
                BuffDurationSeconds = Cfg.BuffDurationSeconds.Value;

                PassiveMode = Cfg.PassiveMode.Value;
                EnableAltAllAtOnce = Cfg.EnableAltAllAtOnce.Value;
                LockConfigOnServer = Cfg.LockConfigOnServer.Value;

                MsgPowerSelected = Cfg.MsgPowerSelected.Value;
                MsgPowerReset = Cfg.MsgPowerReset.Value;
                MsgPowerReady = Cfg.MsgPowerReady.Value;
                MsgPowerLocked = Cfg.MsgPowerLocked.Value;
                MsgNoUnlocked = Cfg.MsgNoUnlocked.Value;

                ReceivedFromServer = false;
            }

            internal static void ApplyFromServer(
                bool debug,
                int cycleHotkey,
                int resetHotkey,
                bool enableResetRemoval,
                float buffCooldownSeconds,
                float buffDurationSeconds,
                bool passiveMode,
                bool enableAltAllAtOnce,
                bool lockConfigOnServer,
                string msgPowerSelected,
                string msgPowerReset,
                string msgPowerReady,
                string msgPowerLocked,
                string msgNoUnlocked)
            {
                Debug = debug;
                CycleHotkey = (KeyCode)cycleHotkey;
                ResetHotkey = (KeyCode)resetHotkey;

                EnableResetRemoval = enableResetRemoval;

                BuffCooldownSeconds = buffCooldownSeconds;
                BuffDurationSeconds = buffDurationSeconds;

                PassiveMode = passiveMode;
                EnableAltAllAtOnce = enableAltAllAtOnce;
                LockConfigOnServer = lockConfigOnServer;

                MsgPowerSelected = msgPowerSelected ?? "Power Selected";
                MsgPowerReset = msgPowerReset ?? "Forsaken Power Has Been Reset";
                MsgPowerReady = msgPowerReady ?? "Ready To Stack Another Power";
                MsgPowerLocked = msgPowerLocked ?? "Forsaken power is locked (boss not defeated yet).";
                MsgNoUnlocked = msgNoUnlocked ?? "No unlocked Forsaken powers yet.";

                ReceivedFromServer = true;
            }
        }

        private void Awake()
        {
            Log = Logger;

            Cfg.Bind(Config);
            Effective.LoadFromLocal();

            _harmony = new Harmony(ModGuid);
            _harmony.PatchAll();

            Log.LogInfo($"{ModName} v{ModVersion} loaded");
        }

        private void OnDestroy()
        {
            try { _harmony?.UnpatchSelf(); } catch { }
        }

        internal static void Dbg(string s)
        {
            if (Effective.Debug) Log?.LogInfo(s);
        }

        // RPC names
        internal const string RpcConfigRequest = "FPP_Config_Request";
        internal const string RpcConfigPush = "FPP_Config_Push";

        internal static bool IsServer => ZNet.instance != null && ZNet.instance.IsServer();
        internal static bool IsClient => ZNet.instance != null && !ZNet.instance.IsServer();

        internal static void RegisterRpcs()
        {
            if (ZRoutedRpc.instance == null) return;

            ZRoutedRpc.instance.Register(RpcConfigRequest, new Action<long, ZPackage>(OnConfigRequest));
            ZRoutedRpc.instance.Register(RpcConfigPush, new Action<long, ZPackage>(OnConfigPush));
        }

        private static void OnConfigRequest(long sender, ZPackage pkg)
        {
            if (!IsServer) return;
            PushConfigTo(sender);
        }

        private static void OnConfigPush(long sender, ZPackage pkg)
        {
            try
            {
                bool debug = pkg.ReadBool();
                int cycleKey = pkg.ReadInt();
                int resetKey = pkg.ReadInt();

                bool enableResetRemoval = pkg.ReadBool();

                float cooldown = pkg.ReadSingle();
                float duration = pkg.ReadSingle();

                bool passiveMode = pkg.ReadBool();
                bool enableAltAllAtOnce = pkg.ReadBool();
                bool lockCfg = pkg.ReadBool();

                string msgSel = pkg.ReadString();
                string msgReset = pkg.ReadString();
                string msgReady = pkg.ReadString();
                string msgLocked = pkg.ReadString();
                string msgNoUnlocked = pkg.ReadString();

                Effective.ApplyFromServer(
                    debug, cycleKey, resetKey,
                    enableResetRemoval,
                    cooldown, duration,
                    passiveMode, enableAltAllAtOnce, lockCfg,
                    msgSel, msgReset, msgReady, msgLocked, msgNoUnlocked
                );

                Dbg("[RPC] Config received from server");
                BossTuning.ApplyPassiveModeAndTuning();
            }
            catch (Exception ex)
            {
                Log?.LogWarning($"[RPC] Failed to parse config push: {ex}");
            }
        }

        internal static void RequestConfigFromServer()
        {
            if (!IsClient) return;
            if (ZRoutedRpc.instance == null) return;

            var pkg = new ZPackage();
            ZRoutedRpc.instance.InvokeRoutedRPC(0L, RpcConfigRequest, pkg);

            Dbg("[RPC] Config request sent to server");
        }

        internal static void PushConfigTo(long targetPeerId)
        {
            if (!IsServer) return;
            if (ZRoutedRpc.instance == null) return;

            Effective.LoadFromLocal();

            var pkg = new ZPackage();
            pkg.Write(Effective.Debug);
            pkg.Write((int)Effective.CycleHotkey);
            pkg.Write((int)Effective.ResetHotkey);

            pkg.Write(Effective.EnableResetRemoval);

            pkg.Write(Effective.BuffCooldownSeconds);
            pkg.Write(Effective.BuffDurationSeconds);

            pkg.Write(Effective.PassiveMode);
            pkg.Write(Effective.EnableAltAllAtOnce);
            pkg.Write(Effective.LockConfigOnServer);

            pkg.Write(Effective.MsgPowerSelected ?? "");
            pkg.Write(Effective.MsgPowerReset ?? "");
            pkg.Write(Effective.MsgPowerReady ?? "");
            pkg.Write(Effective.MsgPowerLocked ?? "");
            pkg.Write(Effective.MsgNoUnlocked ?? "");

            ZRoutedRpc.instance.InvokeRoutedRPC(targetPeerId, RpcConfigPush, pkg);
            Dbg($"[RPC] Config pushed to {targetPeerId}");
        }
    }

    [HarmonyPatch(typeof(ZNet), "Awake")]
    public static class Patch_ZNet_Awake
    {
        private static void Postfix()
        {
            ForsakenPowersPlusMod.RegisterRpcs();

            if (ForsakenPowersPlusMod.IsServer)
                BossTuning.ApplyPassiveModeAndTuning();
        }
    }

    [HarmonyPatch(typeof(ZNet), "OnNewConnection")]
    public static class Patch_ZNet_OnNewConnection
    {
        private static void Postfix(ZNet __instance, ZNetPeer peer)
        {
            if (__instance == null || peer == null) return;

            if (__instance.IsServer())
                ForsakenPowersPlusMod.PushConfigTo(peer.m_uid);
        }
    }

    [HarmonyPatch(typeof(ZNet), "RPC_PeerInfo")]
    public static class Patch_ZNet_RPC_PeerInfo
    {
        private static void Postfix(ZNet __instance)
        {
            if (__instance != null && !__instance.IsServer())
                ForsakenPowersPlusMod.RequestConfigFromServer();
        }
    }

    internal static class BossTuning
    {
        internal static void ApplyPassiveModeAndTuning()
        {
            try
            {
                if (ObjectDB.instance == null || ObjectDB.instance.m_StatusEffects == null) return;

                foreach (var se in ObjectDB.instance.m_StatusEffects)
                {
                    if (se == null) continue;

                    var name = ((UnityEngine.Object)se).name;
                    if (string.IsNullOrEmpty(name)) continue;
                    if (!name.StartsWith("GP_")) continue;

                    if (ForsakenPowersPlusMod.Effective.PassiveMode)
                    {
                        se.m_ttl = 0f;
                        se.m_cooldown = 0f;
                    }
                    else
                    {
                        se.m_ttl = ForsakenPowersPlusMod.Effective.BuffDurationSeconds;
                        se.m_cooldown = ForsakenPowersPlusMod.Effective.BuffCooldownSeconds;
                    }
                }

                ForsakenPowersPlusMod.Dbg("[Tuning] Applied passive mode and buff tuning");
            }
            catch (Exception ex)
            {
                ForsakenPowersPlusMod.Log?.LogWarning($"[Tuning] Failed: {ex}");
            }
        }
    }

    [HarmonyPatch(typeof(ObjectDB), "CopyOtherDB")]
    public static class Patch_ObjectDB_CopyOtherDB
    {
        private static void Postfix()
        {
            BossTuning.ApplyPassiveModeAndTuning();
        }
    }

    [HarmonyPatch(typeof(Player), "Update")]
    public static class Patch_Player_Update
    {
        private static void Prefix(Player __instance)
        {
            if (__instance == null) return;
            if (Player.m_localPlayer == null) return;
            if (!ReferenceEquals(__instance, Player.m_localPlayer)) return;

            if (Input.GetKeyDown(ForsakenPowersPlusMod.Effective.CycleHotkey))
            {
                var next = PowerLogic.FindNextAvailablePower(__instance);

                if (string.IsNullOrEmpty(next))
                {
                    __instance.Message(MessageHud.MessageType.TopLeft,
                        ForsakenPowersPlusMod.Effective.MsgNoUnlocked, 0, null);
                    return;
                }

                __instance.SetGuardianPower(next);
                __instance.Message(MessageHud.MessageType.TopLeft,
                    $"{ForsakenPowersPlusMod.Effective.MsgPowerSelected}: {next.Replace("GP_", "")}", 0, null);
            }

            if (Input.GetKeyDown(ForsakenPowersPlusMod.Effective.ResetHotkey))
            {
                __instance.m_guardianPowerCooldown = 0.1f;

                if (ForsakenPowersPlusMod.Effective.EnableResetRemoval)
                {
                    PowerLogic.RemoveAllGuardianEffects(__instance);
                    __instance.Message(MessageHud.MessageType.TopLeft,
                        ForsakenPowersPlusMod.Effective.MsgPowerReset, 0, null);
                }
                else
                {
                    __instance.Message(MessageHud.MessageType.TopLeft,
                        ForsakenPowersPlusMod.Effective.MsgPowerReady, 0, null);
                }
            }
        }
    }

    [HarmonyPatch(typeof(Player), "StartGuardianPower")]
    public static class Patch_Player_StartGuardianPower
    {
        private static bool _altAtStart;

        // IMPORTANT:
        // bool Prefix lets us block power usage if boss not defeated yet.
        private static bool Prefix(Player __instance)
        {
            if (__instance == null) return true;

            // Read Alt only for local player
            if (Player.m_localPlayer != null && ReferenceEquals(__instance, Player.m_localPlayer))
                _altAtStart = Input.GetKey(KeyCode.LeftAlt) || Input.GetKey(KeyCode.RightAlt);
            else
                _altAtStart = false;

            // Block using locked power (progress gate)
            string gp = __instance.GetGuardianPowerName();
            if (!PowerLogic.IsPowerUnlockedByProgress(gp))
            {
                if (Player.m_localPlayer != null && ReferenceEquals(__instance, Player.m_localPlayer))
                {
                    __instance.Message(MessageHud.MessageType.TopLeft,
                        ForsakenPowersPlusMod.Effective.MsgPowerLocked, 0, null);
                }
                return false;
            }

            return true;
        }

        private static void Postfix(Player __instance)
        {
            if (__instance == null) return;
            if (Player.m_localPlayer == null) return;
            if (!ReferenceEquals(__instance, Player.m_localPlayer)) return;

            if (!_altAtStart) return;
            _altAtStart = false;

            if (!ForsakenPowersPlusMod.Effective.EnableAltAllAtOnce) return;

            // Server authoritative: apply extra effects only on server
            if (!ForsakenPowersPlusMod.IsServer)
            {
                ForsakenPowersPlusMod.Dbg("[AltAll] Client attempted - ignored (server applies)");
                return;
            }

            PowerLogic.ActivateAllUnlockedPowers(__instance);
        }
    }

    internal static class PowerLogic
    {
        // Canonical Valheim boss progression keys.
        private static readonly Dictionary<string, string> PowerToGlobalKey =
            new Dictionary<string, string>(StringComparer.Ordinal)
            {
                ["GP_Eikthyr"] = "defeated_eikthyr",
                ["GP_TheElder"] = "defeated_gdking",
                ["GP_Bonemass"] = "defeated_bonemass",
                ["GP_Moder"] = "defeated_dragon",
                ["GP_Yagluth"] = "defeated_goblinking",
                ["GP_Queen"] = "defeated_queen",
                ["GP_Fader"] = "defeated_fader",

            };

        internal static bool IsPowerUnlockedByProgress(string gpName)
        {
            if (string.IsNullOrEmpty(gpName)) return false;

            // Unknown GP_ (from other mods) should not be hard blocked by our mapping.
            if (!PowerToGlobalKey.TryGetValue(gpName, out var globalKey) || string.IsNullOrEmpty(globalKey))
                return true;

            // During early load, ZoneSystem can be null. Do not hard block.
            if (ZoneSystem.instance == null) return true;

            return ZoneSystem.instance.GetGlobalKey(globalKey);
        }

        private static List<string> GetUnlockedGuardianPowers()
        {
            var powers = new List<string>();

            if (ObjectDB.instance?.m_StatusEffects == null) return powers;
            if (ZoneSystem.instance == null) return powers;

            foreach (var se in ObjectDB.instance.m_StatusEffects)
            {
                if (se == null) continue;

                string name = ((UnityEngine.Object)se).name;
                if (string.IsNullOrEmpty(name) || !name.StartsWith("GP_")) continue;

                // Progress gate only for known vanilla powers. Unknown GP_ allowed.
                if (IsPowerUnlockedByProgress(name))
                    powers.Add(name);
            }

            return powers.OrderBy(k => k, StringComparer.Ordinal).ToList();
        }

        internal static string FindNextAvailablePower(Player player)
        {
            try
            {
                var unlocked = GetUnlockedGuardianPowers();
                if (unlocked.Count == 0) return null;

                string current = player.GetGuardianPowerName();
                if (string.IsNullOrEmpty(current))
                    return unlocked[0];

                int idx = unlocked.IndexOf(current);
                if (idx < 0) return unlocked[0];

                int nextIdx = (idx + 1) % unlocked.Count;
                return unlocked[nextIdx];
            }
            catch (Exception ex)
            {
                ForsakenPowersPlusMod.Log?.LogWarning($"[Cycle] Failed: {ex}");
                return null;
            }
        }

        internal static void RemoveAllGuardianEffects(Player player)
        {
            try
            {
                var seMan = player.GetSEMan();
                if (seMan == null) return;

                var toRemove = new List<int>();
                foreach (var se in seMan.GetStatusEffects())
                {
                    if (se == null) continue;
                    var name = ((UnityEngine.Object)se).name;
                    if (string.IsNullOrEmpty(name) || !name.StartsWith("GP_")) continue;

                    toRemove.Add(StringExtensionMethods.GetStableHashCode(name));
                }

                foreach (var hash in toRemove)
                    seMan.RemoveStatusEffect(hash, true);
            }
            catch (Exception ex)
            {
                ForsakenPowersPlusMod.Log?.LogWarning($"[Reset] Failed: {ex}");
            }
        }

        internal static void ActivateAllUnlockedPowers(Player player)
        {
            try
            {
                string current = player.GetGuardianPowerName();
                if (string.IsNullOrEmpty(current)) return;

                var seMan = player.GetSEMan();
                if (seMan == null) return;

                var activeNames = new HashSet<string>(
                    seMan.GetStatusEffects()
                        .Where(se => se != null)
                        .Select(se => ((UnityEngine.Object)se).name)
                        .Where(n => !string.IsNullOrEmpty(n) && n.StartsWith("GP_")),
                    StringComparer.Ordinal
                );

                var unlocked = GetUnlockedGuardianPowers()
                    .Where(gp => gp != current && !activeNames.Contains(gp))
                    .ToList();

                if (unlocked.Count == 0) return;

                foreach (var gpName in unlocked)
                {
                    int hash = StringExtensionMethods.GetStableHashCode(gpName);
                    var se = ObjectDB.instance?.GetStatusEffect(hash);
                    if (se == null)
                    {
                        ForsakenPowersPlusMod.Dbg($"[AltAll] Missing StatusEffect: {gpName}");
                        continue;
                    }

                    seMan.AddStatusEffect(hash, true);
                }

                ForsakenPowersPlusMod.Dbg($"[AltAll] Activated {unlocked.Count} additional unlocked powers");
            }
            catch (Exception ex)
            {
                ForsakenPowersPlusMod.Log?.LogWarning($"[AltAll] Failed: {ex}");
            }
        }
    }
}
