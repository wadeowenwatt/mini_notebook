import os
import sys


def main():
    # Trong Docker, dùng biến môi trường BOT_TYPE để chọn bot
    bot_type = os.getenv("BOT_TYPE", "").strip()

    if not bot_type:
        # Fallback: cho phép chọn tay khi chạy local
        print("Chọn bot để khởi động / Select bot to start:")
        print("  1. Discord")
        print("  2. Telegram")
        bot_type = input("Nhập lựa chọn (1/2): ").strip()

    match bot_type:
        case "1" | "discord":
            from discord_bot import run

            run()
        case "2" | "telegram":
            from telegram_bot import run

            run()
        case _:
            print(
                "Lựa chọn không hợp lệ. Dùng BOT_TYPE=discord hoặc BOT_TYPE=telegram."
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
