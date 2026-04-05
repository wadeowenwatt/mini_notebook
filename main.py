import sys


def main():
    print("Chọn bot để khởi động / Select bot to start:")
    print("  1. Discord")
    print("  2. Telegram")

    choice = input("Nhập lựa chọn (1/2): ").strip()

    match choice:
        case "1":
            from discord_bot import run
            run()
        case "2":
            from telegram_bot import run
            run()
        case _:
            print("Lựa chọn không hợp lệ. Vui lòng nhập 1 hoặc 2.")
            sys.exit(1)


if __name__ == "__main__":
    main()
