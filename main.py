import subprocess
import os

def run_command(command):
    """Выполняет команду в терминале и возвращает результат."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Ошибка: {result.stderr}")
    return result.stdout.strip()

def choose_device():
    """Выводит доступные диски и запрашивает у пользователя устройство для установки."""
    print("Доступные диски:")
    print(run_command("lsblk -d -o NAME,SIZE,MODEL"))
    device = input("Введите название устройства для установки (например, /dev/sda): ")
    if not os.path.exists(device):
        print("Устройство не найдено!")
        exit(1)
    return device

def get_device_size(device):
    """Получает размер устройства в гигабайтах."""
    size_bytes = int(run_command(f"lsblk -b -dn -o SIZE {device}"))
    size_gb = size_bytes / (1024 ** 3)
    print(f"Размер устройства: {size_gb:.2f} GB")
    return size_gb

def create_partitions(device, swap_size):
    """Создает таблицу разделов и формирует разделы для EFI, SWAP и ROOT."""
    print("Создаем таблицу разделов...")
    run_command(f"parted -s {device} mklabel gpt")
    run_command(f"parted -s {device} mkpart primary 1MiB 1GiB")
    run_command(f"parted -s {device} mkpart primary 1GiB {1 + swap_size}GiB")
    run_command(f"parted -s {device} mkpart primary {1 + swap_size}GiB 100%")

def format_partitions(device):
    """Форматирует разделы и включает SWAP."""
    print("Форматируем разделы...")
    run_command(f"mkfs.fat -F32 {device}1")
    run_command(f"mkswap {device}2")
    run_command(f"mkfs.ext4 {device}3")
    run_command(f"swapon {device}2")

def mount_partitions(device):
    """Монтирует корневой раздел и EFI."""
    print("Монтируем разделы...")
    run_command(f"mount {device}3 /mnt")
    os.makedirs("/mnt/boot", exist_ok=True)
    run_command(f"mount {device}1 /mnt/boot")

def install_base_system():
    """Устанавливает базовую систему Arch Linux."""
    print("Устанавливаем базовую систему...")
    run_command("pacstrap /mnt base linux linux-firmware")

def configure_fstab():
    """Настраивает fstab."""
    print("Генерируем fstab...")
    run_command("genfstab -U /mnt >> /mnt/etc/fstab")

def configure_system():
    """Настраивает системные параметры: время, локали и клавиатура."""
    print("Настраиваем системные параметры...")
    run_command("arch-chroot /mnt ln -sf /usr/share/zoneinfo/Europe/Kyiv /etc/localtime")
    run_command("arch-chroot /mnt hwclock --systohc")
    with open("/mnt/etc/locale.gen", "a") as f:
        f.write("en_US.UTF-8 UTF-8\nuk_UA.UTF-8 UTF-8\nru_RU.UTF-8 UTF-8\n")
    run_command("arch-chroot /mnt locale-gen")
    with open("/mnt/etc/locale.conf", "w") as f:
        f.write("LANG=en_US.UTF-8\n")
    with open("/mnt/etc/vconsole.conf", "w") as f:
        f.write("KEYMAP=us\n")

def install_grub(device):
    """Устанавливает загрузчик GRUB."""
    print("Устанавливаем загрузчик GRUB...")
    run_command("arch-chroot /mnt pacman -S --noconfirm grub efibootmgr")
    run_command("arch-chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB")
    run_command("arch-chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg")

def install_components():
    """Устанавливает основные компоненты для рабочего окружения."""
    print("Устанавливаем основные компоненты...")
    run_command("arch-chroot /mnt pacman -S --noconfirm hyprland waybar fastfetch kitty networkmanager bluez bluez-utils modemmanager modem-manager-gui mesa lib32-mesa vulkan-intel vulkan-icd-loader")

def install_yay():
    """Устанавливает yay для AUR пакетов."""
    print("Устанавливаем yay...")
    run_command("arch-chroot /mnt bash -c 'git clone https://aur.archlinux.org/yay.git /opt/yay && cd /opt/yay && makepkg -si --noconfirm'")

def enable_services():
    """Включает NetworkManager и Bluetooth."""
    run_command("arch-chroot /mnt systemctl enable NetworkManager")
    run_command("arch-chroot /mnt systemctl enable bluetooth")

def configure_theme():
    """Устанавливает тему Catppuccin и настраивает окружение."""
    run_command("""arch-chroot /mnt bash -c '
        git clone https://github.com/catppuccin/gtk.git ~/catppuccin-gtk &&
        mkdir -p ~/.themes &&
        cp -r ~/catppuccin-gtk/Catppuccin-Mocha-Standard-Lavender-Dark ~/.themes/ &&
        gsettings set org.gnome.desktop.interface gtk-theme "Catppuccin-Mocha-Standard-Lavender-Dark" &&
        
        git clone https://github.com/catppuccin/waybar.git ~/catppuccin-waybar &&
        mkdir -p ~/.config/waybar &&
        cp -r ~/catppuccin-waybar/* ~/.config/waybar/ &&
        
        git clone https://github.com/catppuccin/kitty.git ~/catppuccin-kitty &&
        mkdir -p ~/.config/kitty &&
        cp ~/catppuccin-kitty/catppuccin-mocha.conf ~/.config/kitty/catppuccin.conf &&
        
        echo "fastfetch" >> ~/.bashrc
    '""")

def main():
    device = choose_device()
    size = get_device_size(device)
    swap_size = 4 if size < 30 else 8

    create_partitions(device, swap_size)
    format_partitions(device)
    mount_partitions(device)
    install_base_system()
    configure_fstab()
    configure_system()
    install_grub(device)
    install_components()
    install_yay()
    enable_services()
    configure_theme()

    print("Установка завершена! Перезагрузите систему.")

if __name__ == "__main__":
    main()
