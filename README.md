# How to make the 3 Performance Key works on Linux
1. Open a terminal and create this file
```
sudo nano /etc/udev/hwdb.d/90-infinix-gtbook.hwdb
```

2. Paste this
```
evdev:input:b0003v340Ep8002*
 KEYBOARD_KEY_700f6=f13
 KEYBOARD_KEY_700f7=f14
```

3. Then run
```
sudo systemd-hwdb update
sudo udevadm trigger
```
This will set the powersave and balanced to f13 and f14 while performance key already mapped as sleep

# Apps of Infinix GT Book
### Contains:
- ControlCenter
- Gaming Mouse XM01 
- Infinix Apps
- PcConnection

Credit: [Madneess Of Technology](https://www.youtube.com/watch?v=YGb-7-Cq3rQ)

Support Me: <br />
https://saweria.co/kanagawayamada (ID / PH) <br />
https://sociabuzz.com/kanagawa_yamada/tribe (Global) <br />
https://t.me/KLAGen2/86 (QRIS) <br />
