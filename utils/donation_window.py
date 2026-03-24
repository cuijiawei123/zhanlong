# donation_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import os
import sys

def resource_path(relative_path):
    """ 获取资源绝对路径，兼容 PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def open_donation_window():
    win = tk.Toplevel()
    win.title("支持作者 & 免责声明")
    win.geometry("500x600")
    win.resizable(False, False)
    win.focus_set()
    win.grab_set()  # 模态窗口

    # === 免责声明 ===
    disclaimer_text = (
        "⚠️ 免责声明：\n\n"
        "本工具仅用于技术交流与学习研究。\n"
        "使用本工具可能被游戏反作弊系统误判为外挂，请自行承担风险。\n"
        "作者不对任何封号、损失或法律后果负责。\n\n"
        "✅ 建议：\n"
        "- 仅在单机/测试环境使用\n"
        "- 不要用于在线对战\n"
        "- 遵守游戏用户协议"
    )
    tk.Label(win, text=disclaimer_text, justify="left", anchor="w", wraplength=460).pack(pady=10)

    # === QQ群信息 ===
    qq_frame = tk.Frame(win)
    qq_frame.pack(pady=5)
    tk.Label(qq_frame, text="🔔 关注更新：加入QQ群", fg="blue").pack(side="left")
    qq_link = tk.Label(qq_frame, text="点击加群", fg="blue", cursor="hand2")
    qq_link.pack(side="left", padx=(5, 0))
    qq_link.bind("<Button-1>", lambda e: webbrowser.open("https://qm.qq.com/q/你的群号"))  # ← 替换为你的群链接！

    # === 打赏说明 ===
    tk.Label(win, text="\n❤️ 如果觉得有用，欢迎打赏支持作者！", fg="red").pack()

    # === 收款码展示 ===
    try:
        wechat_img = tk.PhotoImage(file=resource_path("images/wechat_pay.png"))
        alipay_img = tk.PhotoImage(file=resource_path("images/alipay.png"))

        # 保存引用防止被回收
        win.wechat_img = wechat_img
        win.alipay_img = alipay_img

        img_frame = tk.Frame(win)
        img_frame.pack(pady=10)

        tk.Label(img_frame, image=wechat_img).pack(side="left", padx=10)
        tk.Label(img_frame, image=alipay_img).pack(side="left", padx=10)

        tk.Label(win, text="← 微信      支付宝 →", font=("Arial", 9)).pack()

    except Exception as e:
        tk.Label(win, text=f"⚠️ 收款码加载失败: {e}", fg="red").pack()

    # === 关闭按钮 ===
    tk.Button(win, text="关闭", command=win.destroy, width=15).pack(pady=15)