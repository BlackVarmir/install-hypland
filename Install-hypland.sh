/bin/bash

# Выводим список дисков с размерами
echo "Доступные диски:"
lsblk -d -o NAME,SIZE
echo ""

# Запросим у пользователя устройство для установки
echo "Введите название устройства для установки (например, /dev/sda):"
read device

# Проверка устройства
if [ ! -b "$device" ]; then
    echo "Устройство не найдено!"
    exit 1
fi

# Узнаем размер раздела
size=$(lsblk -b -dn -o SIZE "$device" | awk '{print $1/1024/1024/1024}')
echo "Размер раздела: $size GB"

# Определяем размеры разделов
if (( $(echo "$size < 30" | bc -l) )); then
    swap_size=4
else
    swap_size=8
fi

# Создаем разделы
echo "Создаем таблицу разделов..."
parted -s "$device" mklabel gpt
parted -s "$device" mkpart primary 1MiB 1GiB   # 1 GB для EFI загрузчика
parted -s "$device" mkpart primary 1GiB "$((1 + swap_size))"GiB   # Раздел под SWAP
parted -s "$device" mkpart primary "$((1 + swap_size))"GiB 100%  # Остальное место под корень

# Форматируем разделы
echo "Форматируем разделы..."
mkfs.fat -F32 "${device}1"   # EFI
mkswap "${device}2"          # SWAP
mkfs.ext4 "${device}3"       # ROOT

# Включаем SWAP
swapon "${device}2"

# Монтируем корневой раздел и EFI
echo "Монтируем разделы..."
mount "${device}3" /mnt
mkdir /mnt/boot
mount "${device}1" /mnt/boot

# Настраиваем зеркало и устанавливаем базовую систему
echo "Устанавливаем базовую систему..."
pacstrap /mnt base linux linux-firmware

# Настраиваем fstab
echo "Генерируем fstab..."
genfstab -U /mnt >> /mnt/etc/fstab

# Настройка времени, локали и клавиатуры
echo "Настраиваем системные параметры..."
arch-chroot /mnt ln -sf /usr/share/zoneinfo/Europe/Kyiv /etc/localtime
arch-chroot /mnt hwclock --systohc
echo "en_US.UTF-8 UTF-8" >> /mnt/etc/locale.gen
echo "uk_UA.UTF-8 UTF-8" >> /mnt/etc/locale.gen
echo "ru_RU.UTF-8 UTF-8" >> /mnt/etc/locale.gen
arch-chroot /mnt locale-gen
echo "LANG=en_US.UTF-8" > /mnt/etc/locale.conf
echo "KEYMAP=us" > /mnt/etc/vconsole.conf

# Устанавливаем загрузчик GRUB
echo "Устанавливаем загрузчик GRUB..."
arch-chroot /mnt pacman -S --noconfirm grub efibootmgr
arch-chroot /mnt grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
arch-chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg

# Устанавливаем основные компоненты (Hyprland, Waybar, fastfetch, Kitty, yay и т.д.)
echo "Устанавливаем основные компоненты..."
arch-chroot /mnt pacman -S --noconfirm hyprland waybar fastfetch kitty networkmanager bluez bluez-utils modemmanager modem-manager-gui mesa lib32-mesa vulkan-intel vulkan-icd-loader

# Устанавливаем yay для AUR пакетов
arch-chroot /mnt bash -c 'git clone https://aur.archlinux.org/yay.git /opt/yay && cd /opt/yay && makepkg -si --noconfirm'

# Включаем NetworkManager и Bluetooth
arch-chroot /mnt systemctl enable NetworkManager
arch-chroot /mnt systemctl enable bluetooth

# Устанавливаем тему Catppuccin и конфигурируем окружение
arch-chroot /mnt bash -c '
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
'

# Завершение установки
echo "Установка завершена! Перезагрузите систему."
