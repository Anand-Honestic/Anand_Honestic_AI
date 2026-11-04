package ai.honestic.athena

import android.app.Application
import android.util.Log

class AthenaApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Log.i("AthenaApp", "ATHENA Phone AI Application Initialized.")
    }
}

