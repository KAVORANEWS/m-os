# M OS input method setup for Plasma Wayland sessions (Fcitx 5, Sinhala input).
#
# SDDM's Wayland session sources /etc/profile, where im-config's
# im-config_wayland.sh would export GTK_IM_MODULE/QT_IM_MODULE=fcitx. On KDE
# Wayland, KWin starts Fcitx 5 as the input method (kwinrc [Wayland]
# InputMethod) and applications should use the Wayland text-input protocol;
# Fcitx warns about these variables ("Wayland Diagnose").
# im-config leaves the environment alone when XMODIFIERS is already set, so
# setting it here (this file sorts before im-config_wayland.sh) is enough.
# XMODIFIERS is still needed for XWayland applications.
# X11 sessions are unaffected: im-config configures them via Xsession.
if [ "${XDG_SESSION_TYPE:-}" = wayland ] && [ -z "${XMODIFIERS:-}" ]; then
    XMODIFIERS=@im=fcitx
    export XMODIFIERS
fi
