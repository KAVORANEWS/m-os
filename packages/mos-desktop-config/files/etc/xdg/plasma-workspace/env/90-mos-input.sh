# M OS input method environment, sourced by startplasma for every Plasma session.
# Fcitx 5 provides Sinhala (Wijesekara / Singlish) input.
#
# Wayland: KWin launches Fcitx 5 as the input method (kwinrc [Wayland]
# InputMethod) and applications use the Wayland text-input protocol.
# GTK_IM_MODULE / QT_IM_MODULE (set by im-config from /etc/profile) must not be
# set there, otherwise Fcitx shows a "Wayland Diagnose" warning and input in
# native Wayland apps can break. XMODIFIERS stays for XWayland applications.
#
# X11: use the classic IM modules.
XMODIFIERS=@im=fcitx
export XMODIFIERS
if [ "$XDG_SESSION_TYPE" = wayland ]; then
    unset GTK_IM_MODULE QT_IM_MODULE
else
    GTK_IM_MODULE=fcitx
    QT_IM_MODULE=fcitx
    SDL_IM_MODULE=fcitx
    export GTK_IM_MODULE QT_IM_MODULE SDL_IM_MODULE
fi
