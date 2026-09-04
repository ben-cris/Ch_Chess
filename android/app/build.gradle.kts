plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

// 复用仓库根目录（xiangqi_assistant）的纯 Python 逻辑包
val pythonRoot = rootProject.projectDir.parentFile

android {
    namespace = "com.bencris.chchess"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.bencris.chchess"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0-m0"
        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false   // Chaquopy 15 与 R8 兼容需按官方处理，M0 先关闭
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }
}

kotlinOptions {
    jvmTarget = "17"
}

chaquopy {
    defaultConfig {
        version = "3.11"
    }
}

// 构建前把 Python 源码同步进 Chaquopy 目录（单一代码源，避免手工复制）
val syncPythonSources = tasks.register<Copy>("syncPythonSources") {
    from(pythonRoot)
    include("core/**", "rules/**", "ai/**", "models/**", "app/**", "engine/**")
    into(layout.projectDirectory.dir("src/main/python"))
}
tasks.named("preBuild") {
    dependsOn(syncPythonSources)
}
