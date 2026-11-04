package ai.honestic.athena.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import ai.honestic.athena.service.AthenaForegroundService

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            AthenaForegroundService.start(context)
        }
    }
}

