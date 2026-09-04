package com.bencris.chchess

import android.app.Activity
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

/** M0：空 UI 骨架，验证 Chaquopy + Python 规则层能在手机上跑通。 */
class MainActivity : Activity() {

    private val mainHandler = Handler(Looper.getMainLooper())
    private lateinit var output: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val title = TextView(this).apply {
            text = "Ch_Chess（象棋辅助）M0"
            textSize = 20f
            setPadding(24, 24, 24, 8)
        }
        val btn = Button(this).apply {
            text = "运行 Python 规则自检"
            setPadding(24, 8, 24, 8)
        }
        output = TextView(this).apply {
            text = "尚未运行。"
            textSize = 13f
        }
        val scroll = ScrollView(this).apply { addView(output) }

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(title)
            addView(btn)
            addView(scroll, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT))
        }
        setContentView(root)

        btn.setOnClickListener { runSelfTest() }
    }

    private fun runSelfTest() {
        output.text = "Python 自检运行中（首次会初始化 Python，请稍候）…"
        Thread {
            try {
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(this))
                }
                val py = Python.getInstance()
                val module = py.getModule("device_selftest")
                val result = module.callAttr("run_self_test").toString()
                mainHandler.post { output.text = result }
            } catch (t: Throwable) {
                mainHandler.post { output.text = "自检异常：${t}" }
            }
        }.start()
    }
}
