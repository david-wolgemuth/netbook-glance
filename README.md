# netbook-glance

A small, keyboard-driven terminal dashboard for answering “what's going on?” on
a resource-constrained laptop or netbook. Its first target is **flyer4**, a
Linux Mint 22 Cinnamon laptop with a Celeron N2930, 4 GB RAM, and about 14 GB
of root storage. It should also be useful on other Linux laptops without
assuming identical hardware.

**Status: minimal working version.** Run `./netbook-glance` in a terminal.
Press `r` to refresh and `q` to quit. The clock and refresh age update once per second; system measurements are collected only on request.

## Goals

- Give a quick, readable view of CPU, memory, swap, battery, Wi-Fi, and root
  filesystem usage on a small screen, with colored bars and percentages where
  useful.
- Stay light on an older CPU and small battery. David observed htop itself
  using around 10% CPU on flyer4; avoid a continuously busy dashboard.
- Run as a standalone terminal program; the user may run it in tmux, but a
  tmux session, launcher, or tmux-specific setup is **not** part of the scope.
- No mouse required. `r` refreshes; `q` quits. Refresh manually by default,
  with no automatic system sampling or persistent service.
- Use existing Linux system interfaces and tools where appropriate. Avoid
  bundling a full system monitor or depending on third-party Python packages.

## Intended display

Layout is illustrative, not a fixed specification:

```text
netbook-glance
Sunday, 22 Nov 2026  09:42:00  (refreshed: 12s ago)

Battery  discharging    [#######---]   72%  3.2 hours

Wi-Fi    connected      [########--]   78%  MyNetwork


CPU      0              [#---------]   13%
         1              [##--------]   16%

RAM                     [####------]   41%
Swap                    [##--------]   23%


Disk     /              [#######---]   69%  4.3 GiB free

r: refresh, q: quit
```

Per-core CPU bars and RAM/swap bars are inspired by the useful top portion of
htop. Prioritize percentages; include free disk space and battery time when
available. Bars and percentages use green/yellow/red according to their meaning: low
battery or Wi-Fi signal and high resource use are highlighted. Labels and
details remain neutral, and numeric values make color optional. Charging/discharging,
unknown time, disconnected Wi-Fi, unavailable swap, missing sensors, and
terminal resize should be handled gracefully. An unavailable measurement must
not prevent the rest of the screen from working. Adapt to narrow terminals and
provide readable fallbacks when color or special glyphs are unavailable.

## Architecture

Begin with one executable Python 3 script, `netbook-glance`, using the Python
standard library and `curses`. Keep the concerns distinct even in one file:

1. **Collection:** read and normalize raw data into a small snapshot. Read
   CPU counters from `/proc/stat`, memory/swap from `/proc/meminfo`, and disk
   capacity via `os.statvfs` or `shutil.disk_usage('/')`. Use `upower` for
   battery state and estimated time; discover the battery rather than assuming
   a particular device path. Use `nmcli` for active Wi-Fi name and signal;
   avoid initiating a wireless scan just to refresh the display. Both tools
   are external system dependencies, not Python packages. Handle missing
   commands, timeouts, missing battery, and disconnected networks as unknown.
2. **Formatting:** compute usage percentages, compact text, thresholds, and
   bars separately from collection and drawing. Show meaningful unavailable
   states instead of treating absent data as zero.
3. **Rendering:** initialize `curses` color pairs where supported and draw the
   snapshot in the available space. Use text and numeric values as well as
   color. Redraw the existing snapshot after a terminal resize.
4. **Input loop:** launch with one refresh, then wait for a key with a
   one-second timeout. `r` gathers a fresh snapshot, `q` exits, and resize
   redraws without collecting. On timeout, update only the clock and time
   since the snapshot; do not run collectors. Use `curses.wrapper` to restore
   terminal state.

CPU usage needs two counter readings separated in time; on initial load and
manual refresh, show a refresh indication, sample at a reasonable short
interval (e.g. 0.5 seconds), and compute per-core deltas. Guard against
zero/invalid deltas. Memory usage should use available memory rather than
simply treating filesystem cache as consumed; be explicit about the formula.
Handle zero swap and avoid division by zero. Subprocesses should have short
timeouts, and data collection should never need sudo. Avoid blocking the UI
indefinitely if a service is absent.

## Scope and possible later ideas

The first implementation needs no process list, configuration framework,
network service, automatic refresh, or tmux integration. If experience shows a
need, consider an optional slow auto-refresh toggle or a key to open a process
viewer; neither is required for the first version. The clock wakes once per second; between these updates and keypresses the
program waits without sampling the system.

## Development and install direction

Python 3 with `curses` should be sufficient on Linux Mint; check availability
on the target instead of assuming every Python build includes curses. `upower`
and NetworkManager (`nmcli`) provide richer laptop information when available.
No Python virtual environment or `pip` dependency should be necessary.

Once implemented and published, the intended lightweight installation is to
clone the repository and symlink its executable into `~/.local/bin`:

```sh
git clone https://github.com/david-wolgemuth/netbook-glance.git ~/projects/netbook-glance
mkdir -p ~/.local/bin
ln -s ~/projects/netbook-glance/netbook-glance ~/.local/bin/netbook-glance
```

For a local checkout, run `./netbook-glance` directly. `~/.local/bin` needs
to be on `PATH`. Update via `git pull` in the checkout.

## Further work

The first version uses ASCII bars for broad terminal compatibility. It shows at
most eight CPU cores so other measurements remain visible. Memory usage is
`(MemTotal - MemAvailable) / MemTotal`; disk usage uses available space as
reported to the current user. Missing commands or devices display as
unavailable. Run `python3 -m unittest -v test_netbook_glance` for tests.

Try it on flyer4 and check idle CPU use and readability. The application has
not yet been tested on that laptop.
