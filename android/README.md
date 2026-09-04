# Android（B1 · M0）—— Chaquopy 工程骨架

目标：原生 Android 壳 + Chaquopy 内嵌 Python，让 `core/rules/ai`（纯 Python，无桌面依赖）
在手机上跑通。当前为 **M0**：空 UI + “Python 规则自检”按钮。

## 目录与版本
- AGP 8.5.2 / Gradle 8.7 / Kotlin 1.9.24 / Chaquopy 15.0.1
- Python（App 内运行）3.11 —— 本机需有 Python 3.11 作为 `buildPython`
  （Chaquopy 会自动找 `py -3.11`，也可在 `app/build.gradle.kts` 里指定 `buildPython`）
- ABI：arm64-v8a（真机）、x86_64（模拟器）

## 首次构建（需要：Android Studio + SDK + 一台手机/模拟器）
1. 安装 Android Studio，并在 SDK Manager 安装：
   - Android SDK Platform 34、Build-Tools
   - 可参考 ``../scripts/setup_android_sdk.ps1``（把 SDK 装到 D:\Android；Chaquopy 无需 NDK）
2. 用 Android Studio **打开本目录** `android/`（首次会自动下载 Gradle 8.7）
3. 手机开启 USB 调试并连接（或启动模拟器）
4. 点 Run ▶ 安装到设备
5. 点“运行 Python 规则自检”，看到 **SELF_TEST PASS** 即 M0 达成

## 说明
- `app/src/main/python/core|rules|ai|models|app|engine` 是构建时由
  `syncPythonSources` 从仓库根（xiangqi_assistant）自动复制的，**不要手工改**；
  逻辑仍以仓库根为准（已加入 .gitignore）。
- `device_selftest.py` 是唯一手写的 Python 入口（手机端自检），改它即可。
- M0 未接入 Compose / 强引擎 / 存取；M1 起按 `../docs/android-port-plan.md` 推进。
