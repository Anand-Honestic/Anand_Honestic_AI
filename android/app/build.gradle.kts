plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    // Note: apply plugin google-services only when google-services.json is present
}

android {
    namespace = "ai.honestic.athena"
    compileSdk = 34

    defaultConfig {
        applicationId = "ai.honestic.athena"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0-rc1"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("debug")
        }
        debug {
            applicationIdSuffix = ".debug"
            isDebuggable = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }

    flavorDimensions += "mode"
    productFlavors {
        create("basic") {
            dimension = "mode"
            versionNameSuffix = "-basic"
            buildConfigField("Boolean", "IS_BASIC_FLAVOR", "true")
            buildConfigField("String", "FLAVOR_NAME", "\"basic\"")
        }
        create("full") {
            dimension = "mode"
            buildConfigField("Boolean", "IS_BASIC_FLAVOR", "false")
            buildConfigField("String", "FLAVOR_NAME", "\"full\"")
        }
    }
}

dependencies {
    // AndroidX Core & UI
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")

    // Hardware Biometrics (Class 3 Fingerprint / FaceID)
    implementation("androidx.biometric:biometric:1.2.0-alpha05")

    // Real-Time WebSocket & Network Engine
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // QR Code Scanning
    implementation("com.journeyapps:zxing-android-embedded:4.3.0")
    implementation("com.google.zxing:core:3.5.3")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.0")

    // Optional Push Notifications (Firebase Cloud Messaging)
    // Conditional or safe compile
    compileOnly("com.google.firebase:firebase-messaging:23.4.1")

    // Unit Testing
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}

// Conditionally apply google-services plugin if file exists
if (file("google-services.json").exists()) {
    apply(plugin = "com.google.gms.google-services")
}
