# Project Status Dashboard

**Last Updated**: 2026-10-18
**Current Phase:** Feature-complete — maintenance & future features

> **A model pushed off the GPU now shows as degraded** (2026-10-18,
> Session 384). A game or a HIP job can move a llama-server's VRAM into
> GTT, system memory reached over PCIe, and it stays there until the
> unit restarts while `/health` keeps answering 200. Each service
> declaring `holds_vram` is now read from DRM fdinfo on every health
> check, and 128 MiB or more off the card reads `degraded`. Estate
> message `af170afe` asked for it after `alfred-inference` sat with
> 1.0 GiB in GTT all evening. `alerts` holds **2** unresolved rows
> <!--check:alerts-->: `Unusual disk / usage`, the anomaly detector
> reading the owner's Steam uninstalls (`/` at 78.2 %, 6.5σ below the
> week's mean), and `Project InvestingAssistant next action idle`. The daemon restarted at **2026-10-18 22:03:29**
> <!--check:deploy--> <!--check:daemon_start-->.

> **Alfred can now read when a game was running** (2026-10-15,
> Sessions 370 and 371). The game detector reads the process list every
> 60 s and keeps one row per stretch a game ran; `GET /api/games/spans`
> serves them raw for Alfred to log as Downtime (ADR-0016). Steam games
> are found by their AppId; others only if listed under `games:` in
> config.yaml. Focus comes from a one-shot KWin script, run only while a
> game is present.

> **/ is 91 % full because of Steam, not the database backups**
> (2026-10-14, Session 364). The critical alert opened at 06:12 BST when
> a Steam update to Last Epoch wrote 21.5 GB in ten minutes. The bigger
> step was Path of Exile 2's install on 2026-09-22, 142 GB in one
> evening. Steam's library is 891 GB of the 1.4 TB used. pgBackRest is
> working as the estate planned: its 2026-10-11 run expired the March
> backup chain and freed 116 GB, and today's 0 ms expire had nothing
> left to remove. Freeing space means uninstalling games, which is the
> owner's call. Separately, the box was powered off by its power key at
> 05:40:48 with no clean shutdown, so the daemon restarted at
> 2026-10-14 05:42:46,
> with the boot.

> **clydeautomation.co.uk is watched** (2026-10-14, Session 363). The
> public site of Clyde Automation, served by Cloudflare with nothing on
> this box, is polled every 5 minutes as `clyde-automation-site`. Asked
> for by its repository; reloaded live, no restart owed. Its first
> reading was `ok`.

> **venture-manager's API goes down when its database does** (2026-10-13,
> Session 360). Its `/api/health` answers 200 even when it cannot read
> its own database, and says `degraded` in the body. The entry now
> carries `expect: { path: status, equals: healthy }`, so that body
> reads down. Its new daily Cloudflare fetch is watched too, as
> `venture-manager-traffic-timer`. Both asked for by venture-manager;
> reloaded live, no restart owed.

> **The database now refuses a duplicate open alert** (2026-10-13,
> Session 359). Until now only the agents' own checks stopped two open
> rows for one alert, or a row marked resolved with no time of
> resolution. Migration 019 makes the database refuse both. The live
> table had no such rows, so nothing changed on the box. Applied live;
> no restart owed.

> **Alfred's Telegram bot is watched** (2026-10-11, Session 358). The
> new `alfred-telegram` entry reads the `telegram` field of Alfred's
> `/api/health` and goes down when it is anything but `ok`: Telegram
> unreachable, a rejected token, or a second poller on the token. It is
> its own entry, like `alfred-bus`, so a bot fault never lowers the
> backend's reliability score. Reloaded live; no restart owed.

> **A critical service now draws a red dot in the tray** (2026-10-11,
> Session 357). Until now it drew the same grey as a service nobody
> checks, because neither of the tray's two colour maps held
> `critical`, `warning` or `skipped`. One map in `sysadmin_tray/styles.py`
> now holds every status the database admits, and a test fails if a
> migration adds one the map lacks. The tray shows it after
> `systemctl --user restart sysadmin-tray`; the monitor needs no restart.

> **A web page can no longer fire the monitor's actions** (2026-10-10,
> Session 356). With no API token set, any page open in a browser on
> this box could restart a service, acknowledge an alert or start a
> scan, because a `POST` with no body reaches the handler before CORS
> hides the reply. Each of the 13 routes that act now refuses a request
> whose `Origin` header names a site outside `service.cors_origins`.
> The tray sends no `Origin` and is unaffected. Another local program
> still can act, and closing that needs the token. To deploy it, the
> owner's restart from a terminal meant the daemon restarted at
> 2026-10-10 16:52:34. Probed live: a foreign origin
> and `Origin: null` both get 403, and a read with a foreign origin
> still gets 200.

> **Four restarts since Session 345's, none of them a fault, and seven
> open alerts where this page named two** (2026-10-08, Session 351).
> The owner restarted the monitor twice by hand on 5 October, at
> 20:29:16 and 21:33:50; the system journal holds both `sudo systemctl
> restart sysadmin.service` commands and no session transcript holds
> either. The first resolved the `Unmonitored systemd units` row a
> minute later, so it most likely loaded other repositories' new
> `services.yaml` entries. The third start, 21:42:10 on 7 October, was
> the reboot into `linux-lts`, and the fourth is the boot after
> Session 349's hard reset: the daemon restarted at
> 2026-10-08 08:49:11 and ran with no restarts until Session 356's. No code changed in between, so
> nothing new was deployed. The five new open rows are named in the
> alert count further down. Three are the sports analyser's, whose units
> the owner had stopped on 7 October; Session 352 set their entries
> `monitor: false` and the three rows resolved. Documentation only.

> **The desktop compositor is not what keeps the graphics card awake**
> (2026-10-06, Session 347). The owner ran last night's measurement with
> administrator rights, so it could see the compositor and the system
> processes for the first time. With both monitors off for almost eight
> hours, the compositor did no work on the card after the minute they
> switched off, and no system process used it at all. Steam was running
> again, though, and its web view drew all night, so the card had a
> visible user throughout and this night alone cannot show more. Put
> together with the Steam-free night of 4 October, what is left is the
> driver or the card's firmware, or something that holds the card awake
> without drawing. Next is one night on the older long-term kernel, with
> Steam quit, which the owner has to start. Documentation only.

> **The owner's unit-file deploy is in, and the monitor now runs every
> fix up to Session 344** (2026-10-05, Session 345). On 4 October at
> 20:50:40 the owner ran `sudo ./scripts/setup-systemd.sh` and then
> `sudo systemctl restart sysadmin` from a terminal, which the system
> journal records with the commands and no session transcript holds.
> That installed the new service file (`Type=notify`, a one-minute
> watchdog) and loaded Sessions 336 to 342. Session 343's junk-growth
> fit was written two minutes later, so it needed one more restart: the
> daemon restarted at 2026-10-05 06:20:53, by Session 345 stopping the main process
> and letting systemd bring it back (12 s down). The tray's "Reaches
> N GB" rows now read 50 GB on 2026-12-30 and 100 GB on 2028-03-11.
> `venture-chat unreachable`, another repository's service, opened and
> closed three times overnight and is closed now, so the open-alert
> count below still holds.

> **A prediction's clock must now stand alone in its sentence**
> (2026-10-04, Session 344). The STATUS checker matches a dated
> prediction to the time its sentence names. It found that time by
> plain substring search, so the `03:00` inside the GPU's address
> `0000:03:00.0`, or inside a time like `15:03:00`, counted as naming
> 03:00. The time must now stand on its own. No restart needed.

> **The junk-growth dates are now fitted over a month, not ten scans**
> (2026-10-04, Session 343). The "Reaches N GB" rows read 50 GB in 2029
> and 100 GB in 2040, because the line was fitted to whatever ten scans
> were newest, and scans bunch up. It is now fitted to every scan from
> the last 30 days. Replayed over the stored history, that window never
> once showed shrinking junk and kept the 50 GB date inside a seven-week
> band. Today it reads 50 GB on 2026-12-29 and 100 GB on 2028-03-08.
> Takes effect at the owner's restart already owed.

> **The tray's "Reaches N GB" rows now show, and their dates are not yet
> trustworthy** (2026-10-04, Session 342). The milestones were 1, 5 and
> 10 GB, and this box has held more than 34 GB of reclaimable files since
> August, so none of the rows ever showed. They are now a ladder up to
> 100 GB, and only the rungs above today's total are shown. They show 50
> and 100 GB today. The dates they carry (2029 and 2040) come from a fit
> over the 10 newest scans, which sees too little of the series. The
> whole series reaches 50 GB in about three months. Fixing the fit is
> the next action. Applied live by a config reload.

> **The junk-growth forecast no longer drops a milestone that is due now**
> (2026-10-04, Session 341). This is the same fix as the disk forecast
> below, applied to the "Reaches N GB" rows in the tray's disk panel. It
> has never mattered here: the box has always held more than 34 GB of
> reclaimable files, so all three milestones (1, 5 and 10 GB) were passed
> long ago, and those rows have never been shown. Whether the milestones
> should change is recorded as a task. Takes effect at the owner's
> restart already owed.

> **The disk forecast no longer misses a crossing that is due now**
> (2026-10-04, Session 340). When disk usage was rising fast enough
> that its trend line had already passed 80 % but the latest reading had
> not, the forecast said the disk was "not on current trend" and raised
> no warning. In late August that happened on the five days before the
> disk crossed 80 %, and each of them reported "90 % in 18 days" instead.
> It now reports the crossing as due today and ranks it first. Takes
> effect at the owner's restart already owed.

> **The monitor's last restart was the owner's, and is now on record**
> (2026-10-04, Session 339). This page said the monitor last restarted
> on 2 October; it has been running since 3 October. The daemon
> restarted at 2026-10-03 09:55:07, by the owner from a venture-manager
> session, so that it would start watching venture-manager's new backup
> timer. It does: the timer read `ok` from its first check at 10:00.
> That restart also loaded the faster advice pages (Session 333). The
> recovery notices (Session 336), the tray-only presence check (Session
> 337) and the new service file still need the owner's restart.
> Documentation only.

> **Steam was not the only thing keeping the graphics card awake**
> (2026-10-04, Session 338). Last night the owner quit Steam, and its
> web view did stop drawing. With both monitors off for nearly 11 hours,
> no program the measurement can see used the card for whole minutes at
> a time, yet the card never powered down. Something it cannot see holds
> the card: the desktop's compositor, a system process, or the driver.
> The card has not powered down once since the 28 September system
> update, which changed the kernel, the card's firmware and the desktop
> together. Next is the same overnight measurement run with
> administrator rights, which the owner has to start.

> **Only the tray now counts as watching** (2026-10-04, Session 337).
> The monitor stays silent while the tray is running, so the two never
> both pop up the same alert. It decided that by noticing anything
> reading the alert list, so a one-off command-line check could keep it
> quiet as well. The tray now names itself on every request, and only a
> request carrying that name counts. Takes effect at the owner's
> restart already owed.

> **The monitor now says when an outage it announced is over**
> (2026-10-03, Session 336). When the tray is not running, the monitor
> pops up its own alerts, and until now it said only that something had
> broken, never that it was fixed. Now a fault it announced gets a
> "Recovered" notice once the alert closes, folded into one notice when
> several close together. It speaks only about faults it announced
> itself, and only if the alert closed since it last checked, so old
> alerts do not come back as news after a restart. Takes effect at the
> owner's restart already owed.

> **Found what keeps the graphics card awake all night: Steam's
> built-in web view** (2026-10-03, Session 335). With both monitors off
> from 22:31 to 08:50, the card never powered down. It was never idle
> for more than 1 second, and it needs 5 seconds idle before it suspends.
> With no monitor attached, the X11 compatibility layer gives windows a
> stand-in refresh of once a second. Steam's web view drew a frame on
> every tick, about 55,000 times, and logged each one as a "bogus refresh
> interval". On the one recent night the card did sleep, Steam was
> running but its web view was not drawing. Held awake and idle, the
> card drew a median of 28 W. A second night's measurement is scheduled
> for tonight; it confirms the finding only if Steam's window is closed
> to the tray or Steam is quit.

> **The slow service-advice page no longer freezes the monitor's
> request loop** (2026-10-02, Session 333). That page took up to
> 9 seconds and blocked every other request, and the watchdog's
> heartbeat, for up to 4 seconds of it. Measured on a copy under the same
> CPU limit: the work now runs on a separate thread and fetches only the
> four fields it reads instead of whole records. The worst wait for
> another request fell from 4.2 to 0.67 seconds, and the page itself
> from about 6 to under 4 seconds. The reliability page got the same
> treatment. The small remaining wait is recorded. Takes effect at the
> owner's restart already owed.

> **The monitor's unit file now asks systemd to restart it if it
> freezes** (2026-10-02, Session 332). It declares that the monitor
> reports when it is ready and sends a heartbeat. If no heartbeat arrives
> for 60 seconds, systemd kills and restarts it. The period was chosen by
> measuring how long the monitor's request loop really stalls: one
> rarely used advice page holds it for up to 9 seconds. A heartbeat goes
> out every 30 seconds, so that page cannot trigger a restart. The page
> has slowed from 1 to 9 seconds since August, so fixing it is now a
> task. Takes effect when the owner redeploys the unit file.

> **The monitor can now tell systemd it is ready and still alive**
> (2026-10-02, Session 331). This is the code half of the planned
> watchdog: once startup finishes the monitor says "ready", then sends a
> heartbeat every few seconds from the same loop that answers requests,
> so if that loop freezes the heartbeats stop and systemd restarts it.
> Under the current unit file nothing listens, and the code stays
> silent. Tried on throwaway units: a healthy one stayed up and one
> with a frozen loop was killed 3 seconds later. The unit-file half is
> next.

> **The monitor's failure alarm now fires once, when systemd gives up**
> (2026-10-02, Session 330). Until now it also fired on every failed
> start along the way, about six times for one crash loop. Each firing
> sent a critical notification saying the monitor was down for good
> while systemd was still restarting it. One setting in the unit file
> (`RestartMode=direct`) makes it fire only at the restart limit; this
> was tried on throwaway units first. A single crash that recovers now
> appears only in the journal. That has not happened since mid-August:
> every early firing was part of a loop that hit the limit anyway. It
> takes effect when the owner redeploys the unit file.

> **The way back from the monitor's planned watchdog is written down
> and rehearsed** (2026-10-02, Session 327). A planned change makes
> systemd kill the monitor if it stops reporting that it is alive. If
> the change goes wrong, the steps to undo it now sit in the unit file,
> and each was tried on a throwaway copy: a broken start reaches
> `failed` after about 8 minutes, a plain reload does not stop the
> kills, and `reset-failed` is needed before it will start again. The
> rehearsal also found that the failure alarm fires on every failed
> start, not only at the restart limit as the file claims (recorded,
> not fixed). Comments and a test only. The installed unit file needs
> redeploying to match.

> **STATUS.md's alert count reads 2 again** (2026-10-02, Session 326).
> The block counted 3 unresolved alerts and named `venture-chat
> unreachable` as the third; that row resolved at 09:32. `Estate queue
> starved`, opened after the last count, resolved by itself at 11:07.
> The two open are `Critical disk usage on /` and `Project ImbaBots next
> action idle`. Documentation only.

> **A live journal test no longer fails while a GPU lease waits**
> (2026-10-02, Session 325). One test checks that the log-format
> detector can answer "no" for the estate API's journal. It read the
> newest record, expecting plain text. While a GPU lease waits, the
> estate logs a JSON line every few seconds, so the newest record was
> JSON a third of the time and the test failed. The cause had been
> recorded wrongly as an empty window. The test now reads up to a moment
> it has already confirmed ends on plain text. Test only; no restart.

> **The graphics card stays awake at night because of the desktop, not
> the kernel** (2026-10-02, Session 324). Yesterday's reading blamed
> the 28 September kernel update. The record says otherwise: the card
> suspended on only one night since 10 September, the night every
> desktop app was closed before the monitors went off, and it stayed
> awake for 13 nights on the older kernel too. Measured live, several
> desktop apps (Spotify, Steam, Firefox, Xwayland) send work to the card
> every second. An overnight recorder runs tonight to find which of
> them keep doing so with the monitors off. Script and documentation
> only; no restart.

> **The 5-minute poll no longer wakes a suspended graphics card**
> (2026-10-02, Session 323). When the RX 7900 XTX is in runtime
> suspend, the collector now skips `rocm-smi` and reads nothing of the
> card except its power state. Its temperature, VRAM and power are
> left blank for that poll. On the night of 27–28 September that call
> woke the card 93 times. The overnight test of which reads are safe
> found the card awake all night, and it has not suspended once since
> the 28 September kernel update, so today's change has nothing to act
> on yet. The daemon restarted at 2026-10-02 11:06:32
> to load it.

> **README's service count reads 37 again** (2026-10-02, Session 322).
> go-to-market's persona model was added to `services.yaml` and the
> README figure was not, so `test_readme_claims` was red. Documentation
> only.

> **A service that changes state during a failed run is still
> announced on the next one** (2026-10-02, Session 321). The monitor
> remembers each service's last announced status so that it speaks only
> on a change. Since yesterday's fix a failed run stays silent, but it
> still updated that memory, so the next run saw no change and the
> transition was never announced. The memory now moves only once the
> run's data has been saved. The daemon restarted at 2026-10-02
> 09:06:57 to load the change.

> **A failed agent run no longer announces alerts that were never
> saved** (2026-10-01, Session 320). When an agent raised an alert and
> then failed, the database threw the alert away but the service still
> told its listeners about it. The desktop notifier then showed a
> notification for an alert that did not exist, and could do so even
> while an older alert with the same title was already open, which is
> the case it is meant to keep quiet. A failed run now announces only
> that it failed. The daemon restarted at 2026-10-01 22:00:32 to load
> the change.

> **Critical alerts now go out on the estate's message bus**
> (2026-10-01, Session 318). Until today every alert this service
> raised reached only a screen on this machine. Each newly raised
> alert at `critical` (the level is a setting) is now also published
> to the estate's MQTT broker on `estate/alerts/raised`, as
> `sysadmin-publisher`, so something away from the desk can pick it
> up. Nothing subscribes to that topic yet: the phone app needs a
> renderer for it first, which was requested from alfred-glance the
> same evening, and whether to build one is that repository's call. The daemon
> restarted at 2026-10-01 21:26:01 to load the change, and a test publish
> from the new code reached the broker as that identity.

> **This block agrees with the box again** (2026-10-01, Session 317).
> Four of its statements had gone out of date during the day, and each
> was re-measured before it was changed. At the owner's `sudo
> systemctl restart`, the service restarted at 2026-10-01 15:12:12,
> after the restart Session 312 recorded. One of the three open alerts the block counted
> resolved at 14:36, so two are open. Session 316 added a test and left
> the test count one short. And two port alerts the block set aside as
> flapping have not been seen for seven days, so those two declarations
> were retired. No service code changed. The owner then restarted it
> again, at 20:30:10, which put three
> changes live, measured at 21:01. venture-chat is polled on its new
> port 8301 and venture-manager's API on 8900, both `ok`, and
> `GET /api/projects/managed` returns 32 projects, the one more that
> Session 316's discovery depth added.

> **This service now sees the same set of projects as the estate**
> (2026-10-01, Session 316). The estate began looking one folder level
> deeper for projects today, counting a folder at that depth only if it
> declares itself a project. This service still looked two levels down,
> so it was missing one project the estate knew about,
> `automation-side-income`. Its search depth now comes from the
> estate's own setting, so the two agree, and will keep agreeing if the
> estate changes it again. It takes effect at the next restart of the
> service.

> **The test suite is green again** (2026-10-01, Session 315). Three
> live checks had failed because of changes made elsewhere today. The
> README's count of monitored services was one short after
> venture-manager added its API. A snag entry claimed the generated
> health-check address is wrong for most services; it is now wrong for
> exactly half, so the entry was narrowed to what still holds: it is
> wrong for services that answer a different address. The third failure
> cleared on its own once the estate's audit re-ran after a project
> folder moved. No service code changed and no restart is owed.

> **A one-night test of which reads leave the sleeping card asleep is
> scheduled** (2026-10-01, Session 314). From 01:30 to 05:30 on 2
> October a temporary timer will take one reading at a time while the
> card is powered down, and record whether the card woke. The readings
> are `rocm-smi` limited to the built-in graphics, and the card's own
> temperature, power and memory files. Two controls run beside them:
> one does nothing, which gives the rate at which something else wakes
> the card, and one is today's call, which is known to wake it. The
> results are read the next morning and decide the fix. No service
> code changed.

> **This service's 5-minute poll wakes the sleeping graphics card**
> (2026-10-01, Session 313). Measured over the night of 27 September,
> when the monitors were off: the kernel logged the card waking 283
> times, and every one of the 93 polls that found it asleep was followed
> by a wake 2–3 seconds later. That is a third of the night's wakes; most
> of the rest were the local model server doing real work. The wake
> comes from `rocm-smi`, run for temperature, memory and power. Session
> 310's change, below, relabelled the busy figure but did not stop the
> wake. Decided: stop it. How is the next task, because it first needs
> a reading of which queries leave a sleeping card asleep. No code
> changed.

> **A failed language-model call now logs the server's own reason**
> (2026-10-01, Session 312). When the local model server refuses a
> request, the log used to record only the HTTP status, and one status
> covers several causes: a 500 is both a full context window and a
> request the server could not read. The shared library now parses the
> server's error text and type, and both are logged beside the status,
> empty when the server sent no such text. Daemon restarted at
> 2026-10-01 14:21:43.

> **SearXNG's warnings are stored readably** (2026-10-01, Session
> 311). The estate's SearXNG shim now writes its log lines as JSON. Its
> one warning, that SearXNG itself cannot be reached, would have been
> stored with the whole JSON document as its title. `services.yaml` now
> declares the format, so the message is lifted out. The check that each
> such declaration is still true would have failed the next morning,
> because the shim writes JSON only when it starts; it now reads the
> start of the current run. Applied by a live reload, no restart.

> **A sleeping GPU now reads 0 % busy, and says why** (2026-10-01,
> Session 310). When the monitors are off, the graphics card powers
> itself down, and the shared GPU library now reports it as 0 % busy
> instead of "unknown". Stored as it came, that 0 would have claimed a
> reading of the card's busy counter that never happened. Each row now
> labels it `runtime-pm`, meaning the power manager answered. The old
> "unknown" path asked `rocm-smi`, which woke the card to measure it: 92
> rows on the night of 27 September, 17 of them non-zero. Daemon
> restarted the same afternoon.

> **Every registry load now takes the configured discovery depth**
> (2026-10-01, Session 309). `discovery_depth` was passed by the unit
> sweep alone; the services registry, the reload, the projects route and
> the unit advice took estate-lib's default. Both read 2, so nothing
> differed on the box, but setting the key would have given the sweep a
> different project set from the one `services.yaml` is checked against.
> All six calls pass it, an AST guard refuses one that does not, and the
> reload classifies it as live. Daemon restarted at 2026-10-01 13:03:27.

> **`projects_root` is a top-level config key** (2026-10-01, Session
> 308). It sat under `agents.project_organiser`, an agent that left for
> the estate on 2026-08-13, and none of its seven readers was that agent.
> It and `discovery_depth` moved to the top level, and the organiser's
> config block and model are gone. A copy left at the old path is named
> as an unknown key on startup and every reload, never silently obeyed.
> Daemon restarted at 2026-10-01 12:27:15.

> **Growth resuming after a big cleanup now raises a disk risk within days,
> not a month** (2026-10-01, Session 307). The disk forecast fitted one
> line over 30 days, so after the late-July cleanup it reported "not
> growing" until 24 August while usage climbed back past 80 % on the 31st.
> It now also fits the last 7 days and keeps the sooner crossing; replayed
> over the stored history, the warning would have appeared on 12 August.
> The short fit can only add urgency, never remove it. Tray restarted,
> daemon restarted at 2026-10-01 10:26:43.

> **The installed system units are now checked against git** (2026-10-01,
> Session 306). The test that already caught a `sysadmin*` user unit
> differing from git now also reads `/etc/systemd/system`, where
> `sysadmin.service` had kept a retired `After=` line for a month
> unnoticed. Both installed system units match git; the check skips
> where none is installed, as in CI. Tests only; no restart owed.

> **The installed backend unit now matches git** (2026-10-01, Session
> 305). `/etc/systemd/system/sysadmin.service` had still ordered itself
> after `ollama.service`, the LLM runtime retired on 2026-07-24, a month
> after git dropped that line. The owner redeployed it with
> `scripts/setup-systemd.sh`, and the installed file is now
> byte-identical to git's. Ordering is read only at start-up, so no
> restart was owed.

> **The tray's launcher is now the one in git** (2026-10-01, Session
> 304). dotfiles found the installed `sysadmin-tray.service` user unit
> in no repository, while this one versioned a KDE autostart entry
> instead. Measured: the unit alone launches the tray, and the autostart
> entry had never been installed. The unit is now tracked byte for byte,
> the autostart file is gone, and `scripts/setup-systemd.sh` installs
> the unit and removes any old autostart entry, because the tray has no
> single-instance guard and both together would start two trays.
> Nothing in the daemon changed; no restart owed.

> **A nudge's wording is now this repository's alone** (2026-10-01,
> Session 303). estate-manager deleted the title, message and details
> its `Nudge` computed and never sent (their ADR-0217), so the snag
> recording two owners of that wording, `SNAG-ESTATE-002`, is closed.
> The check that watched for their fix saw it and is retired, with its
> 10 tests. The alert titles this repository raises for idle projects,
> such as `Project Athenaeum next action idle`, do not change. Only
> comments and docstrings changed in the daemon's code, and the restart
> was paid anyway so the box matches the tree: daemon restarted at
> 2026-10-01 08:19:33.

> **The first boot under mosquitto's start gate was clean** (2026-10-01,
> Session 302). estate-manager's gate holds the MQTT broker back until
> its LAN address is assigned, because a broker started too early used
> to crash and, on 3 of 10 boots, lose its saved messages. At the
> 2026-09-30 21:37:30 BST boot it held the broker back once, for 5
> seconds, and the broker then started with no crash and its saved
> messages intact. The hold-back still raises one self-closing `Failed
> to start` warning a boot, which is now filed as a known snag.
> Documentation only; no restart owed.

> **The log trend report now serves every message logged this
> fortnight** (2026-09-30, Session 301). Its size cap went from 2,000 to
> 5,000 distinct log messages, after measuring what that costs. At 2,000
> the cap cut messages that logged this fortnight, so 9 faults showed a
> week's count too low. The cost is reading the whole log table, which
> the cap does not change (165 ms capped against 200 ms uncapped); the
> cap only limits what comes back, at about 5-7 µs a message. Live, the
> report is no longer truncated and serves all 301 faults, 171 new.
> Daemon restarted at 2026-09-30 22:19:24.

> **The status block is level with the box again after a GPU reset and
> a reboot** (2026-09-30, Session 300). At 20:28-20:29 UTC amdgpu logged
> a page fault from a `VKRenderThread` (a graphics program's render
> thread), failed to reset the stuck graphics ring, and reset the whole
> GPU, so every client lost its VRAM. That opened 17 alerts: 16 kernel
> log errors and the critical `GPU was reset` row. Three minutes later
> two venture-assistant pipeline jobs failed to connect, 19 in all. All
> 19 closed on their own by 20:47:49 UTC. The box then rebooted at
> 21:37:30 BST, which restarted the inference server the earlier 17:50
> reset had left holding a dead GPU context, and its `llama-server
> degraded` row closed at 20:42:51 UTC. The boot raised mosquitto's and
> Alfred's backend's `Failed to start` warnings again; both units came
> up, and both rows closed at 20:54:48 UTC. Documentation only, and the
> daemon start moved without a deploy: daemon restarted at
> 2026-09-30 21:37:44, by the reboot.

> **The GPU reset test no longer breaks on a real reset**
> (2026-09-30, Session 299). A live test plants a fake GPU reset in the
> log table and checks the monitor finds it. The fake was dated
> 8 September, so today's real reset at 17:50 UTC was newer and the
> monitor rightly reported that one instead, turning the suite red. The
> fake is now dated just after the newest real reset. Its leak check
> had also stopped being able to see a leaked fake behind the real
> reset, and now counts the row directly. Test only, no restart owed.

> **The log trend report's size cap now cuts by a stated rule**
> (2026-09-30, Session 298). The cap keeps 2,000 distinct log messages
> of about 2,470. Which ones went used to be the database's choice, and
> it dropped 35 faults that logged this fortnight. The obvious fix,
> keeping recent messages first, would have made 18 old kernel faults
> look new, because a fault is dated by its oldest message. So the cap
> now keeps the oldest message of each shape (the text with its numbers
> blanked) first, then the busiest this week. Live, the report serves
> all 291 faults and all 161 new ones; 7 still lose part of a week's
> count. The restart was owed and paid: daemon restarted at
> 2026-09-30 21:06:32.

> **Measured: the log trend report's size cap drops real faults**
> (2026-09-30, Session 297). The trend query keeps at most 2,000
> distinct log messages. This box has 2,461, most of them one-off lines
> that differ only by a process id. On the live table the cap removes
> 35 fault signatures that logged this fortnight, 7 of them first seen
> this week. Which ones go is decided by the database's internal order
> among messages tied at one line each, not by any stated rule. Filed as
> `SNAG-LOG-020` with three shapes of fix. Measurement only, no restart
> owed. *(Fixed by Session 298, above.)*

> **A live test now pins which log trend counts are windowed**
> (2026-09-30, Session 296). It puts three rows of one fault in the real
> database (this week, last week, and three weeks ago) and checks that
> the trend report counts one in each week but three in `total`, and
> dates the fault from the oldest. The rows are rolled back. The test
> proved it can fail: making `total` count only the two weeks turns it
> red. Test only, no restart owed.

> **The log trends contract now says which counts are windowed**
> (2026-09-30, Session 295). In each fault signature on
> `GET /api/logs/trends`, `current` and `previous` count this week and
> last week, while `total`, `first_seen` and `last_seen` span all 30
> days of retained logs. That is deliberate, because "new" means never
> seen in retained history, but the contract never said so; on the live
> box 79 of 235 signatures have a `total` larger than the two weeks
> added together. Docstring only, no behaviour change. The restart was
> owed and paid: daemon restarted at
> 2026-09-30 16:10:56.

> **The weekly log review now keeps to its 150-word limit too**
> (2026-09-30, Session 294). Every log review the model had written ran
> over, between 190 and 211 words. The disk review's fix (shorten once,
> then cut at the last full sentence with a marker) moved into shared
> code, and both reviews now use it, each with its own shortening
> prompt. On the Monday job's path, six of eight live drafts ran over
> and the shortening pass brought all six in without a cut. One
> shortened draft kept its headings and lost the service names under
> them, so a shortened review is not always better than a cut one. The
> health review needs nothing: its reviews run about half the limit.
> The restart was owed and paid: daemon restarted at
> 2026-09-30 07:04:13, then again for Session 295.

> **The weekly disk review's narrative keeps to its 150-word limit**
> (2026-09-29, Session 293). The model was told the limit and kept it
> about half the time; six of the seven stored reviews ran over, the
> longest at more than twice the length. Now a review that runs over is
> sent back once to be shortened, and whatever is still over is cut at
> the last full sentence that fits, with a marker saying it was cut. On
> the Monday job the second pass brought every long draft in without a
> cut. The `POST` route cannot take the second pass, because the GPU
> check reads the review's own first pass as someone else's work, so
> route-made reviews are cut instead (`SNAG-GPU-007`). The log review
> breaks the same limit and is a task of its own. The restart was owed
> and paid: daemon restarted at
> 2026-09-29 22:18:35.

> **A prediction cannot be pinned by a clock the block states in another
> sentence, and now a test says so** (2026-09-29, Session 292). Every
> hour-and-minute this block has ever written, 214 of them, is planted
> against a prediction whose own sentence does not name it, and none
> pins. The live prediction is also driven with its clock taken out of
> its own sentence; the six other places the block says that hour do not
> hold it up. One gap is left and filed as `SNAG-DOCS-032`: inside its
> own sentence the pin is still a substring match, so a device address
> such as `0000:03:00.0` would count as `03:00`. Tests only; no restart
> owed.

> **Our 8500 row in the estate's port registry names this project**
> (2026-09-29, Session 291). The owner ruled that a row's Project cell
> holds the claimant's directory name or `.project.yaml` id. Ours said
> `sysadmin-service`, the `services.yaml` name, which matches no
> project, so this repository corrected it to `sysadmin-assistant` in
> estate-manager's tree, committed on its own and announced there.
> estate-manager's resolver now resolves every row in the table.
> `SNAG-ESTATE-005`, which had recorded the row since 2026-08-15, is
> closed and its check retired. No restart owed.

> **mosquitto's boot core dump stays `critical`, for new reasons**
> (2026-09-29, Session 290). The estate's fix is already installed and
> loaded (the entry below says it was still to come, which was out of
> date), but no boot has run under it yet. It holds the broker back
> until its address is assigned, and each refusal logs the same
> `Failed to start` warning a genuine failure does. That leaves the
> core dump as the only alert that says the broker started too early.
> Under the fix it should never fire, so quietening it would save
> nothing. The dump was never a sign of the lost state; watching for
> that loss directly is now an idea. Documentation only; no restart
> owed.

> **The broker lost its state to a completed save, not to the crash**
> (2026-09-29, Session 289). estate-manager's reply to our two mosquitto
> filings (message `a5c95062`) read the journal back to 2026-08-11, and
> it holds on re-reading. When mosquitto fails to bind at boot it saves
> its database on the way out. Each time that save finished (three
> boots, two of them with no crash) the next start came back empty; each
> time a crash cut the save short (seven boots), the old file survived.
> Four places here had blamed the crash and now carry correction notes.
> The estate's fix makes the broker wait for its addresses before
> starting; the owner has still to install it. Whether the core dump
> should stay `critical` now its stated reason is gone is a new task.
> Documentation only; no restart owed.

> **CI passes on GitHub for the first time** (2026-09-29, Session 288).
> Once estate-manager pushed its `main`, the 36 tests that needed its
> newer estate-lib passed and nothing else failed. The first green runs
> are 36564522725 and 36564524086: 4,160 passed. `GitHub Actions` is now
> in `.project.yaml`'s stack, so web/cv's CV may claim it
> (`SNAG-TEST-015` closed). No `sysadmin/` change; no restart owed.

> **The boot default names a kernel branch, not a version**
> (2026-09-29, Session 287). Kernel upgrades had orphaned the boot
> default three times, because it named a single version's boot entry;
> the loader then fell back to sort order and could boot LTS unasked.
> The owner set it to a glob matching whichever mainline entry is
> installed. No code change; no restart owed.

> **CI leaves out the tests that read this box, and says so**
> (2026-09-28, Session 286). 104 tests carry a `box` pytest marker and
> the GitHub workflow runs `pytest -m "not box"`; the box still runs
> everything and stays green. Sorting the failures by reason found three
> that were not the box, fixed in the workflow instead: a shallow
> checkout, the runner's UTC clock, and its older Python patch release.
> The first run (36467479237) failed 36 tests, exactly the ones that
> need estate-manager's unpushed code (`SNAG-TEST-015`). No `sysadmin/` change; no restart owed.

> **CI now gets past `uv sync`** (2026-09-28, Session 285). The GitHub
> workflow checks out estate-manager beside this repository, using a
> read-only deploy key because that repository is private. Ruff runs
> green on GitHub for the first time. Pytest is still red
> (`SNAG-TEST-015`): about 80 tests read this box itself, and
> estate-manager's pushed code is behind the box's. No `sysadmin/`
> change; no restart owed.

> **This project's stack and features are declared for the estate**
> (2026-09-28, Session 284). `.project.yaml` now lists what the
> repository runs on and what it can do, each feature dated by the
> commit that first carried it, so web/cv's CV can build its line for
> this project from the estate board instead of typing it. The log file
> tailer and service auto-restart are declared `prototype`: both are
> built and neither is used. GitHub Actions is left out of the stack,
> because CI has failed on every GitHub run since the remote was created
> (`SNAG-TEST-015`: the runner cannot find `estate-lib`). No `sysadmin/`
> change; no restart owed.

> **The weekly reviews have their LLM back** (2026-09-28, Session 282).
> All three weekly reviews used the LLM this morning, and the GPU
> arbiter's lifetime grant count reads 82, off the 67 it was stuck at.
> The stall that cost the 2026-09-21 narratives lasted 48 hours and
> ended on its own at 2026-09-22 00:01:04; today's review leases were
> granted within 6 seconds. `SNAG-GPU-003` (the lease and its fallback
> gate read the same busy floor) is lowered P2 → P3 because the stall
> has not recurred. Documentation only; no restart owed.

> **Mosquitto's boot core dump stays `critical`** (2026-09-28, Session
> 281). The broker crashes on most boots when a listener binds before
> `eno1` holds its address. `coredumpctl` shows two different crashes:
> seven since 2026-09-03 fault inside the database save and the store
> survived, and today's faults after the save and the store came back
> empty. Their log signatures differ, so the harmless-looking one could
> have been quietened on its own. It was not, because both come from
> one race whose fix belongs to estate-manager and is still open, and
> the other outcome of that race has now lost data. estate-manager has
> the corrected stacks (reply `af040aab-eef6-406b-a311-e04f67337273`).
> Documentation only; no restart owed. *(Corrected by Session 289: the
> crash did not lose the data. A failed bind's completed save did, with
> or without a crash, and the seven write-path crashes kept the store by
> interrupting that save.)*

> **The 11:49 reboot's three alerts, accounted for** (2026-09-28, Session
> 279). Each one was a boot-order race that systemd's first retry healed
> about 5 seconds later, and all three closed on their own at 12:06:19,
> after the log aggregator's 15-minute quiet window. Mosquitto started
> before `eno1` held 192.168.1.2 and got `Cannot assign requested
> address` binding that listener. It then crashed on the way out, in
> `sub__clean_session` during `context__cleanup` (a segfault in 2.1.2's
> error-path teardown, after the database save). That raised the
> critical `dumped core` alert and the `Failed to start` warning. It
> came up at 11:49:19. Alfred's backend ran its `alembic upgrade`
> at 11:49:10, four seconds before PostgreSQL was listening, was refused
> on 5432, and started at 11:49:16. **This is not new:** a
> core dump follows the same bind error on every boot in the journal
> since 2026-09-03, eight of them, and the critical alert has opened and
> closed on nine boots since 2026-08-17. *(Corrected by Session 281: this
> said "the same core dump". The earlier seven fault inside the database
> save, not in `sub__clean_session`.)* **One thing was new today:** the
> start after the crash restored 0 retained messages and 0 subscriptions,
> where every earlier boot restored 2 and 8. The broker belongs to
> estate-manager, so Session 280 sent them that finding as register
> message `e1eef46b-05cc-4460-9968-abb7524d0232`; it was not worked
> here. Documentation only; no restart owed.

> **A long traceback keeps its cause in the stored log row** (2026-09-28,
> Session 278, `SNAG-LOG-019`). `raw_line`, the journal record kept beside
> each log row as evidence, was cut at 2,000 characters, which dropped a
> traceback's last line: the exception itself. The owner chose to raise
> the cap, and it is 32,000 now, one constant used at all three places
> the old number stood. Over 30 days no record but a core dump exceeded
> 7,702 characters. Rows stored earlier keep their cut. The restart was
> owed and paid once: daemon restarted at
> 2026-09-28 15:06:45.

> **`CLAUDE.md`'s design narrative lives in `docs/design/` now**
> (2026-09-27, Session 272). About 3,940 lines of per-session reasoning
> moved verbatim into one file per domain, and `CLAUDE.md` keeps a pointer
> line per file. Every session loads `CLAUDE.md`, so each now starts with
> about a sixth of what it used to read. Documentation only; no restart owed.

> **A finished agent run names the process that ran it** (2026-09-27,
> Session 270). `_record_outcome` used to replace `details` whole, so the
> instance stamp the startup sweep reads disappeared the moment a run
> finished. A `completed` or `failed` row now keeps it beside the run's own
> details: live, 0 of 180 finished rows carried it before the restart, and
> every row finished after it does. The stamp is written again rather than
> merged with SQL `||`, because a merge would carry the sweep's
> `cancelled_by` onto a run that went on to finish. One `sysadmin/` file
> changed, so the restart was owed and paid once.

> **This service now serves the health path it tells every other project
> to serve** (2026-09-27, Session 268). `GET /api/health` answers from the
> same handler as `/health`, and our own `services.yaml` row polls it, so
> the monitorable-project contract's path is used here rather than only
> recommended. `/health` stays for the tray's liveness probe, and the
> access-log exclusion covers both. Estate-manager was told in message
> `37ac5331`, so its registry can drop the `health:legacy` marker on 8500.
> The restart was owed and paid once: daemon restarted at
> 2026-09-27 15:59:12.

> **The estate's `pointers` check is not judged here, and the one place its
> findings can come from is guarded instead** (2026-09-27, Session 264,
> ADR-0015). The check looks at estate-manager's own snag list, and only a
> write to ours can open either of its codes, so a test now pins this
> repository's fifteen `SNAG-ESTATE-*` ids. `JUDGED_AUDIT_CHECKS` is
> unchanged. One `sysadmin/` file changed (a comment), so the restart was
> owed and paid once: daemon restarted at 2026-09-27 06:11:40.

> **A GPU lease held for want of free VRAM is no longer blamed on a stopped
> tick loop** (2026-09-26, Session 262, closing `SNAG-GPU-006`). Since
> estate-manager's ADR-0202 the arbiter holds a waiter when the card is busy
> *or* when free VRAM is short of the grant's net need plus headroom; the
> judge knew only the first. `Estate queue starved` under `nothing_granted`
> now reads `vram_floor` beside `gpu_floor`, applies the producer's own
> comparison to the producer's operands, and names the VRAM limb when it is
> the one holding. The busy floor keeps precedence, as it does in the tick.
> The title does not move; the live population is zero. One `sysadmin/` file
> changed, so the restart was owed and paid once: daemon restarted at
> 2026-09-26 21:10:16.

> **The estate's wiring check and this monitor are now compared on which
> `settings.json` they read** (2026-09-26, Session 260, closing
> `SNAG-CFG-007`). The estate publishes the file its wiring check opened, as
> `inputs.settings_file` on `/api/audit/invariants`; the judge compares it
> with the file this repository reads and raises one `warning` row, `Estate
> wiring check and this monitor read different settings files`, if they
> differ. The comparison counts as read only when both halves were and the
> estate named a file, so a run with 8400 dark, or a producer that stops
> publishing the field, neither raises nor clears it. Today both resolve to
> `/home/gaddi/projects/dotfiles/claude/settings.json`. Three `sysadmin/`
> files changed, so the restart was owed and paid once: daemon restarted at
> 2026-09-26 18:30:13.

> **A broken manifest in another repository no longer stops this daemon, and
> the owner hears about it** (2026-09-25, Session 259, closing
> `SNAG-SVC-007`). Every `load_registry` call here passes `partial=True`
> (estate-manager's ADR-0201), so a tree whose `.project.yaml` will not load
> is left out and named, where one bad file anywhere under `~/projects` used
> to fail the boot. A refused tree that `services.yaml` references still
> fails it, and the estate library's own `registry_manifest_refused` WARNING,
> written first, says why. The estate judge raises one `warning` row per
> refused tree off `refused_manifests` on `/api/projects/attention`, titled
> `Project manifest <tree> refused`. The unit sweep keeps a refused tree as a
> live project, so its units are not reported as orphans: 22 of the box's 43
> hand-written units sit in the five trees `services.yaml` references. Seven
> `sysadmin/` files changed, so the restart was owed and paid once: daemon
> restarted the same day, the instant now carried by the block above.

> **Alfred's MQTT connection is watched from its own health route** (2026-09-25,
> Session 257, by the owner's decision on Session 252's open item).
> `alfred-bus` reads `bus` out of `:8100/api/health` and is `degraded`
> whenever it is not `"ok"` — the one sub-status on the box nothing else
> sees, because Alfred's probe connects with its own credentials and so
> catches a live broker refusing it. venture-assistant's `:8300` and the
> SearXNG shim's `:8600` were declined: every limb of the first is its own
> entry here, and the second already answers 424 for a failed search.
> Alfred was told first (estate message `b5191cf0`). services.yaml only, so
> deployed by reload, with no restart owed.

> **A degraded alert says why, and the fix waits on another repository's
> YAML to deploy** (2026-09-24, Session 253, closing `SNAG-SVC-006`). The
> message now ends `; last check: <reason>`, so a stalled pipeline toasts
> `stalled is true, expected false` instead of only "degraded for 3
> consecutive checks". The 4xx branch and a still-`activating` unit write a
> `reason` too — searxng's HTTP 424 was the only degraded cause in the last
> thirty days and carried none. The restart waited on
> `~/projects/archive/bsl-translator/.project.yaml`, malformed from its commit
> `bb51480` until the owner's `fedf248` at 10:38, because `load_registry`
> raises on it and the lifespan does not catch that (`SNAG-SVC-007`). Paid
> once the manifest parsed: daemon restarted at 2026-09-24 13:47:34, the
> boot's registry load reading 28 of 28 declared, and estate messages
> `faae94f1` and `6b140d86` closed on it. The owner then restarted it
> three times with `sudo systemctl restart` from a terminal in
> estate-manager — 13:56:50 onto their `features:` key (their `0f0f788`),
> 14:34:48 for a reason neither repository records, and once more that
> afternoon onto their `parts:` key (their `7401bfc`) — each the same clean
> 28-of-28 load. Session 255 delegated the lasting fix
> for that class (`SNAG-SVC-007`) to estate-manager.

> **A health check reads the body when the route says so** (2026-09-23,
> Session 252, estate message `ed301e95` from venture-assistant). Their
> dedupe stalled 44 hours while every route we poll answered 200; the route
> that knew — `/pipeline/status`, `stalled: true` — answered 200 too.
> `kind: http` entries now take `expect: {path, equals}`, and
> `venture-pipeline` is declared with it. Unmet or unreadable is `degraded`.
> Two `sysadmin/` files changed, so the restart was owed and paid twice (the
> second for the reason's JSON spelling): daemon restarted at
> 2026-09-23 22:46:33, and
> `venture-pipeline` read `ok` at 21:51:35 UTC.

> **`nothing_granted` names its limb, and the comparison the estate left us is
> made with its operator** (2026-09-22, Session 249, estate message
> `a3923a29` read whole and closed). The queue surface's new `gpu_floor`
> (their ADR-0189) carries the arbiter's last floor reading and its own
> threshold with no verdict; `judge_queue_invariants` makes the comparison
> under `nothing_granted` with `Arbiter.tick`'s strict `>` against the
> published comparand, so a starved row now says whether the card was over
> the threshold or the tick loop has stopped granting. An absent `gpu_floor`
> keeps the two-limb sentence; the reading's age is stated and never
> thresholded. One `sysadmin/` file changed, so the restart was owed and paid
> once: daemon restarted at 2026-09-22 19:15:10, `NRestarts` 15 → 16,
> `/health` answers 200.

> **The collector reads the counter the gate reads, and the ordering was half
> the fix** (2026-09-22, Session 248, closing `SNAG-GPU-004` and
> `SNAG-GPU-005`). `gpu_percent` for the dGPU is now
> `estate.gpu.sample_gpu_busy` resolved by PCI slot; `rocm-smi` keeps product
> name, temperature, VRAM and power. So *"how busy does this service say the
> card is"* and *"is the card too busy to dispatch"* stopped being two
> instruments answering in one vocabulary — one counter, one device, named
> once in `config.llm.gpu_pci_slot`.
>
> **The entry recorded the ordering as corroboration and it is a rule.** Its
> bracketing run — a sysfs read sd **0.2** before one `rocm-smi` call and
> **3.1** ~55 ms after, off the same file — means a fix that sampled the
> counter *after* spawning the subprocesses would inherit the perturbation it
> exists to remove, pass every test written for it, and merely measure less
> badly. The call is made first, and a test pins the call *order*, which no
> assertion about the returned value can see.
>
> **Measured within one run either side, because across runs the card moves.**
> Interleaved arms, same card, n=20 each: before, the collector read sd **9.5**
> over **6–51** while the counter beside it read sd **2.7** over **12–25**;
> after, both arms read sd **0.5** over **12–13** and agreed on min, max, mean
> and sd. The entry's "13× noisier" was an across-run ratio; the within-run one
> is 3.5×, and only the second is a comparison.
>
> **Every row says which instrument answered it**, on both paths and for both
> cards, because a perturbed reading and a clean one are the same integer in
> the same field. The iGPU keeps `rocm-smi`'s figure — `sample_gpu_busy`
> answers for one slot — and `gpu_percent_source` is what keeps the mixed
> payload legible rather than silent. Every row also carries `pci_slot`, which
> is `SNAG-GPU-005`: `rocm-smi`'s `card0` is the dGPU and DRM's `card0` is the
> iGPU, so the key was a vocabulary and never an identity.
>
> **The historic rows are deliberately not backfilled.** The one fallback
> specimen carries `card0` at 2048 MB beside `card1` at 24560 — it identifies
> its own devices from inside itself, so nothing is recoverable that a reader
> does not already have, and writing today's enumeration onto a seven-week-old
> row asserts a mapping no evidence from that day supports. `message_backfill`
> could repair its rows because `raw_line` made the repair exact; there is no
> such witness here, and a repair that cannot be witnessed is refused rather
> than approximated. Live either side of the restart: the stored row reads
> `gpu_percent: 15` from `sysfs` beside VRAM **12,902 MB** and **85 W**, where
> the 36 rows inside the estate's coverage runs had been reading below their
> own minimum floor while carrying ≥ 10,476 MB. Suite **4205 → 4221**, green
> (4219 passed, 2 skipped); ruff and mypy clean. Two `sysadmin/` files changed
> and the tree was frozen before the restart was paid, so it was paid once:
> daemon restarted at 2026-09-22 17:16:04, `NRestarts` 14 → 15, `/health` answers **200**.

> **The estate's sampler was right, and the instrument that was wrong was
> ours** (2026-09-22, Session 247, reading estate message `160c0f32` whole and
> closing it; reply filed as `1c9616ca-ab7a-4e97-8892-78b809972d8a`). Their
> reply established that the arbiter's GPU floor reading is live on every tick
> and reads **low** — both the opposite of what `SNAG-GPU-003` inferred — and
> then stopped at the seam, because estate rule 1 forbids them reading our
> database. The one explanation left sat on the side neither party had
> instrumented, and it is this repository's.
>
> **`_from_rocm_smi` perturbs the number it reports.** It launches two
> `rocm-smi` subprocesses concurrently, one of them querying temperature,
> meminfo and power, and those sensor queries are themselves GPU work landing
> inside the window the utilisation figure is averaged over. Three arms,
> interleaved, same card, same minute, thirty samples each: sysfs
> `gpu_busy_percent` sd **0.7**, a single `rocm-smi --showuse` sd **0.8**, our
> production collector sd **9.3** — with two readings of exactly **0** against
> a card sitting steadily at 13 %. `rocm-smi` is not the culprit; our
> invocation is.
>
> **The figure this service publishes is therefore not the counter the GPU
> gate reads**, and nothing said so. Under production spacing, 36 snapshots
> fall inside the estate's two coverage runs of 2026-09-21; **16 read below
> 38 %** — their minimum floor, itself a min-of-4 that can only read low — and
> **4 read exactly 0**, while the same rows carry VRAM ≥ 10,476 MB and power
> ≥ 85 W. The rows refute themselves in two other columns.
>
> **Every previous check of this reader passed because they compared means.**
> Over that coverage our mean is **40.6** against their 38–40: the two
> instruments agree on the mean and disagree entirely on the spread. This
> sitting made the same mistake in its own first fifteen minutes before a run
> reporting spread separated them, which is why `SNAG-GPU-004` says so rather
> than implying it. A verification that takes the wrong statistic is not weak
> evidence — it is evidence for a different claim.
>
> Opened `SNAG-GPU-004` (P2, **owed** — the collector perturbs its own
> reading) and `SNAG-GPU-005` (P4, owed — the sysfs fallback keys on `cardN`,
> so `card0` is the iGPU on that path, one live specimen in 3,574 rows). The
> two refuted bullets of `SNAG-GPU-003` are struck in place rather than
> deleted and it moves `blocked` → `decided`; its structural finding, *a lease
> is not a place to wait for a floor*, never depended on whose instrument was
> right and is untouched. The fix is named and deliberately unwritten: it
> changes a production collector on a 300 s loop and is owed tests, including
> one pinning the **spread**, since every existing test of that module pins a
> value and a value is what was never wrong. No `sysadmin/` file changed this
> sitting, so the restart Session 246 paid still stands and none is owed.

> **The field ledger has a floor now, and the composition it replaces is
> green under the one mutation that breaks it** (2026-09-22, Session 246,
> closing `SNAG-BRIEF-007`). `tests/test_briefing_fields_are_additive.py`
> drove `_every_branch_taken()` and nothing else, so *"a consumer always
> receives `Entries`, `Errors` and `Sources`"* was true of this producer and
> asserted nowhere. `FLOOR_FIELDS` states it and six tests hold it.
>
> **The composition that looked sufficient was driven rather than argued
> about.** It reads: the sibling pins that `Overnight Logs` arrives having
> gathered nothing, this file pins that its keys are those three, therefore
> the three always arrive. The second premise is the conditional one — it is
> measured at a payload **with data in it**, and this file reads its keys
> back off a *render*, which is honest only while the producer spells them
> as literals. Turning that section's `data` into a comprehension leaves
> `tests/test_briefing_sections_are_additive.py` **entirely green, 21
> passed**, while reddening three tests here. Not a shape invented for the
> argument: `Filesystem` has been exactly it since 2026-08-11
> (`SNAG-BRIEF-006`), and it is a *ledgered* section that stopped being one.
>
> **The sibling's floor drive is self-asserting and this one is not**, which
> is the test this sitting would not have written from the handoff. The
> sibling renders one section where its ceiling renders six, so pointing it
> at the wrong fixture reddens it. Measured here, the floored section serves
> the same three names under **both** fixtures — so swapping
> `_nothing_gathered()` for `_every_branch_taken()` leaves every floor
> assertion green and the module claiming a guarantee it never measured. A
> guard's fixture choice is part of its claim, so it has an assertion of its
> own: the floor payload is a *strict* subset of the ceiling payload.
>
> **The emptiness problem is answered structurally, where the ledger beside
> it needed a synthetic.** A parametrised guard over an empty mapping is
> green without running; `RETIRED_FIELDS` answers that with a forged
> retirement and a floor has no forgery available. Totality answers it
> instead — a floored title that cannot be excused must be ledgered — so the
> population cannot reach zero while the sibling declares a floor at all.
>
> **Six mutations driven, all six land on the intended tests, none green.**
> Five are caught here and nowhere else in the suite.
>
> Suite **4199 → 4205**, green (4203 passed, 2 skipped); ruff and mypy
> clean. One `sysadmin/` file changed and it is a docstring — the sentence
> naming which module holds which half, which this change made wrong — so
> the restart was paid once, after the tree was frozen. *(Previously restarted
> at 2026-09-22 10:18:45, `NRestarts` 13 → 14, `/health` 200 — demoted and
> unbolded by Session 248, which paid the next one; two bolded timestamps in
> this region union into one `unknown` claim naming both.)* estate message `160c0f32` was left
> **open** deliberately, Session 245 having judged it a reply worth a sitting
> of its own — **read, answered and closed by Session 247**, which is the
> block above.

> **The omit rule has an exception, and the exception is a guarantee**
> (2026-09-21, Session 245, discharging Session 244's handoff and closing
> estate message `4bccc5e9`). The briefing producer's section list has a
> **floor of one**: five of its six sections are appended behind an `if`
> and `Overnight Logs` is not, so a consumer receives at least one section
> whatever the box has been doing, and `metrics` is the one `type` this
> producer can never drop. That was true and unstated; it is stated in
> `render_sections`' own docstring now and pinned by seven tests.
>
> **The claim it corrects was in this tree, not only in theirs.**
> estate-manager filed the measurement because their `estate-map.md`
> argued that a seam check cannot compare section sets *because* an
> omitting producer's list moves with its data — and the sentence it
> argued from, *"sysadmin omits sections rather than sending them
> empty"*, is false at one section. The same sentence, unqualified, was
> the second paragraph of our own producer's docstring, eleven lines
> above the counterexample and its explaining comment. The floor is a
> **second and independent** reason that check is blind, and it sat
> inside the sentence offered as the first.
>
> **Their item was not redundant, and checking that is what took the
> sitting.** They offered to withdraw it if the fact was stated somewhere
> they had not looked. Three places state the **premise** — `_gather_logs`
> says it never returns `None`, the comment over the append says a count
> is always available, and [ADR-0014](../adr/0014-a-sample-cannot-be-both-pinnable-and-real.md)
> §2 re-measured the one-unconditional figure on 2026-09-14 — and every
> one of them is about the *producer*. A floor of one, and a `type` a
> consumer is guaranteed, are about the **payload**. Nothing stated that.
>
> **The measurement was reproduced two ways before it was acted on**, not
> accepted: an independent `ast` walk gives 5 guarded and 1 unconditional,
> and driving `render_sections` at an empty `gathered` returns exactly
> one section, `Overnight Logs`, type `metrics`.
>
> **The guards that exist could not have caught it, and one of them had
> it in its hands.** Both additive-only ledgers drive
> `_every_branch_taken()`, a payload built to make every conditional true;
> a fixture of that shape cannot observe a floor. And
> `tests/test_health_review.py` builds the empty payload exactly and asks
> only whether one title is *absent* — the floor rendered in front of it,
> unasked.
>
> **One of the new tests was measured empty before it was believed.** The
> premise that the floor fixture makes every gated key falsy walked the
> `if` tests for `gathered[...]` subscripts; the producer binds each key
> to a local first and gates on the local, so it resolved **0** keys and
> would have passed over `_every_branch_taken()` itself. It resolves the
> alias now, finds **5**, and carries an anti-vacuity assert of its own —
> the registry rule *a name is not a parse*, one module over.
>
> **Eight mutations driven, all eight land, none green.** The one that
> matters is `if True:` round the floor section: the drive stays green and
> only the source walk reddens, which is exactly why the structural half
> is not the behavioural half restated — a floor that holds by the *value*
> of a condition holds until someone edits the condition.
>
> Suite **4192 → 4199**, green (4197 passed, 2 skipped); ruff and mypy
> clean. One `sysadmin/` file changed and it is a docstring, so the
> restart was paid once, after the tree was frozen, and `/health` answered
> 200 on the new process. The instant it carried is git's now, not this
> block's: two timestamps in the parsed region make the `daemon_start`
> claim read one figure two ways. `SNAG-BRIEF-007` records what was
> deliberately not done one level down.

> **The reading returned the opposite of its premise, and the lease was
> never granted** (2026-09-21, Session 244, discharging Session 243's
> handoff and opening `SNAG-GPU-003`). The scheduled weekly-review reading
> is taken and both halves are negative: `llm_used` is **false** on all
> three review tables, and the 05:00 lease-hold split is **unmeasurable**
> rather than unchanged. No code changed, so no restart is owed.
>
> **Nothing on this box has been granted a GPU lease since 2026-09-20
> 00:01:03**, which is the standing condition a sitting should know before
> planning anything that wants the card. `grants_total` has read **67**
> throughout; five consecutive leases were dropped with `granted_at` null —
> `venture-drain`'s nightly, our three weekly reviews, and
> **estate-manager's own weekly review**. So this is not `SNAG-SCHED-003`'s
> contention behind a declared holder: there was no holder, and the party
> that wrote the arbiter paid the same price we did.
>
> **The arbiter was ticking and declining, not stalled**, which is the
> discrimination the whole finding turns on. It logged `lease N waits: GPU
> floor X% over threshold 25%` every ~6.5 s across the window, and its
> process has been up since 2026-09-13 with no commit touching GPU
> arbitration since — so the condition changed and the code did not. That
> rules out the first limb of our own alert's disjunction and leaves the
> second.
>
> **A lease is a place to wait for a holder, and not a place to wait for a
> floor.** `gpu_lease.py` rule 1 degrades every refusal to
> `ensure_gpu_idle`, and both halves read the same sysfs counter against
> `llm.gpu_busy_threshold`, which defaults from
> `estate.gpu.DEFAULT_BUSY_THRESHOLD` and is not overridden here — one
> home, by the design `sysadmin/core/config.py` argues for in writing. The
> unstated consequence is that the grant is gated on the same predicate the
> fallback gate then re-asks, so waiting 55, 40 and 10 minutes bought a
> refusal at `busy_percent: 39` against `threshold: 25`. That is a limit of
> `SNAG-SCHED-003`'s fix rather than a defect in it.
>
> **Every component behaved as documented and the judging spoke first.**
> `judge_queue_invariants` raised `Estate queue starved` at 00:20:52 and
> again at 05:20:52, both `warning`, both since resolved, carrying
> `waiting_reason: nothing_granted`. **Its second limb is the true one** —
> *"or its GPU sampler is pinned by undeclared load"* — which is
> `_WAIT_CAUSES`' refusal to name a single cause paying off on the first
> morning it could.
>
> **Two false trails are recorded because both were nearly filed.** Read
> truncated at 160 characters that alert message looks like it asserts the
> *first* limb, and a finding against our own renderer was averted only by
> reading the column whole. And our own collector was suspected of
> under-reporting on `SNAG-SCHED-003`'s recorded `card0`/iGPU trap; driven
> against sysfs in the same instants it agrees to sampling noise, with
> `card0` resolving to the discrete card and the iGPU flat at zero. Cleared
> by measurement rather than by argument.
>
> **Filed at the owner as friction, message
> `806b1c71-eeb4-4f19-80e1-d26ada1913c6`**, which reported that the
> arbiter has granted nothing for 37 hours and asked the one question this
> side cannot answer: whether its floor is read on every tick or once and
> reused. Deliberately **not** a request to move the threshold —
> `DEFAULT_BUSY_THRESHOLD`'s own comment already declares it an inherited
> convention nobody has measured. Raising our own copy is refused in
> writing on `SNAG-GPU-003`: it restores the narratives without restoring
> the lease, and re-introduces by hand the third transcription the single
> home exists to prevent.
>
> **`SNAG-GPU-001`'s population is unchanged and extends rather than
> turns**: newest GPU reset still 2026-09-06 20:43:01, now **14.8 days**,
> with no line newer across any boot. This Monday's digests are **not**
> evidence about that entry, because the LLM was never reached — the class
> was not exercised in either direction.

> **A prediction the calendar kept, and the key it was argued over was
> never the right one** (2026-09-21, Session 243, discharging Session 242's
> handoff and closing `SNAG-LOG-014`). Retention emptied that entry's
> population on the morning its own `expires` marker named: the oldest
> retained `sysadmin.service` row is ingested **2026-08-24 07:54:54**, the
> duplicate count is **0**, and nothing was deleted by hand. The check
> retires with the entry and the detector does not —
> `tests/test_log_resume_boundary.py::TestNoJournalRecordIsStoredTwice`,
> `FROZEN_TABLES`' rule, in `SNAG-LOG-007`'s own file because the residue
> was that mechanism's.
>
> **The re-homed guard is keyed on neither key the entry argued between,
> and the column that settles it was in the table throughout.** That entry
> weighed `(source, logged_at, message)` against `(source, logged_at)` and
> took the narrow one. Both are wrong for a *guard*: the narrow key is
> blind to the only recorded form of this defect, the two copies having
> carried different messages and hidden each other for eleven days; and the
> wide key now has a live false positive. `raw_line` holds the journalctl
> record verbatim and no repair rewrites it, so one raw line under two rows
> is one record stored twice and two raw lines are two records. That is
> `SNAG-LOG-008`'s own witness rule applied one entry over, where it had
> been available and unused.
>
> **The entry's supporting figure was refuted three days after it was taken
> and was attached to the wrong key.** It stated *zero groups share a
> `(source, logged_at)` while disagreeing about `message`* and *the
> tightest gap between two genuinely distinct records from one source is
> 3 µs, at the kernel*. On 2026-09-07 the 05:00 health review wrote
> `llm_unavailable` and `health_review_llm_unavailable_used_fallback` at one
> `__REALTIME_TIMESTAMP` — two records, **0 µs** apart, from
> `sysadmin.service`. Re-measured: 0 is the tightest gap between two
> records from one source, and 3 µs is the tightest between two *identical*
> lines, which is the **narrow** key's margin stated in a sentence about
> the wide key's. The choice was right and its reason is demonstrated now
> rather than argued.
>
> **The retired check would have called that coincidence a duplicate.** Its
> divergence clause renders *"N of them agree on the record and not on the
> message, which is this entry's own pre-backfill shape"* whenever the wide
> count exceeds the narrow one, and against the live specimen both limbs
> are false. It was written when the class had no members and read as a
> definition; one member turned it into a claim.
>
> **The family keeps a live member, and the new prediction is the old
> arithmetic reapplied.** That coincidence is what gives the guard's
> discrimination a live specimen, and it ages out by the same fixed-hour
> purge `SNAG-LOG-014` was corrected for on 2026-09-04: ingested
> 2026-09-07 05:00:54, so thirty days lands that evening and the 2026-10-07
> run reaches nothing. Driven at the real `purge_statement` rather than
> re-derived — **0 of 2** on 2026-10-07 and **2 of 2** on the next. The row
> clears at 03:00 on 2026-10-08, after which
> `test_a_shared_instant_is_two_records_and_not_one_stored_twice` skips for
> want of a specimen rather than passing.
> *(Measured 2026-10-08 by Session 351: the first half came true and
> the second did not. No shared instant from 2026-09-07 is left, but
> the test passes rather than skips, because 53 other instants are
> each shared by two records with different raw lines: 52 from
> `venture-assistant-backend.service` on 24 to 26 September and one
> from `sysadmin.service`. The specimen family grew while it waited.
> The test will skip only if no new shared instant is ingested
> meanwhile. The newest of the 53 was ingested 2026-09-26 22:52:19.
> Driven at the real `purge_statement` and rolled back, the 26 October
> run leaves **1 of 53** and the next leaves **0 of 53**, so today's
> specimens clear at 03:00 on 2026-10-27, GMT by then.)*
> <!--check:expires 2026-10-27T03:00+00:00 the 53 shared instants measured on 2026-10-08 clear at retention-->
>
> **One falsification passed against deliberately broken code, and the
> mutation drive's restore failed silently before it.** Inverting the
> discrimination left the file green, its population being the groups that
> *agree* about `raw_line` and that population being empty on a healthy box
> — `SNAG-TEST-010`'s shape. The predicate is named and driven at a
> fabricated agreeing group now. Separately the first drive's `cp` restore
> targeted a scratchpad directory that did not exist, so three mutations
> stacked and every reading after the first measured the wrong tree:
> Session 242's *"a mutation drive whose restore is not observable measures
> the previous mutation as often as the current one"* by a second route,
> an untracked file there and a missing directory here. The restore carries
> a checksum witness now.
>
> **A red suite hid three vacuous-guard findings for a day.**
> `check-vacuous-guards.sh` exits 2 on a red suite and reports nothing — its
> own rule that a red suite is not *its* finding — so Session 242's known-red
> live check blinded the measure running beside it. Three sites in
> `tests/test_briefing_fields_are_additive.py` surfaced the moment the suite
> went green, and none is a defect: `RETIRED_FIELDS` is empty *by measurement*
> and that file's docstring argues it at length, so the reasoning existed in
> prose and had never been declared to the guard built for it. Three
> declarations, no behaviour changed, 5 → 8 and 18 → 19 declared. Confirmed to
> predate this sitting by driving the script at HEAD, where the report is empty
> for the same reason. **A sitting that knowingly ships a red suite also spends
> that day's vacuous measurement**, and neither the handoff nor this block said
> so.
>
> **The file owed a premise it had never owed before.** `SNAG-TEST-007`'s
> rule 2 binds a live drive in a file off the `*_live.py` glob, and
> re-homing the detector made `test_log_resume_boundary.py` one — the
> convention catching a file that became a live drive rather than one
> written as one.

> **A ledger of titles says nothing about the names inside them, and the
> third section stopped spelling its own** (2026-09-20, Session 242,
> discharging Session 241's handoff and opening `SNAG-BRIEF-006`).
> `tests/test_briefing_fields_are_additive.py` extends the additive-only
> guard one level down, to the `data` field names the producer writes as
> literals. Suite **4170 → 4195**, green; ruff and mypy clean; nothing under
> `sysadmin/` changed, so no restart is owed.
>
> **The scope the handoff measured was right about today and blind to
> yesterday.** It said 2 of 6 sections carry literal `data` keys, and they
> do. Walking the producer's history *before* writing the ledger — all 15
> commits under both of its paths — says **three** titles have ever carried
> them. `Filesystem` published `disk_used_percent`, `reclaimable_mb`,
> `empty_dirs`, `stale_project_dirs` and `duplicate_groups` until
> 2026-08-11, when the section became a comprehension; `_gather_filesystem`
> returns all five to this day. It is `SNAG-BRIEF-005`'s shape one level
> down — a name that stops being *spelled* looks exactly like one that stops
> being *served*.
>
> **The two ledgered sections break differently at the consumer, and a
> ledger that did not say so would assert something false about one of
> them.** Measured in Alfred's tree rather than inferred from the section
> contract. A `status_grid`'s field names are a **vocabulary it looks up by
> name**, with fallbacks that are precisely what makes a rename quiet:
> `all_ok` falls back to `all_services_healthy` and then to `None`, and
> `entries` falls back to `services` and then to `[]`, which renders as
> `status="empty"`. A `metrics` section's keys are passed through verbatim
> and `DigestMetrics.vue` states in writing that the field set is **open**,
> humanising each key generically. So a rename is silently **dropped** in
> one section and silently **relabelled** in the other. Both are quiet, so
> both are ledgered; the remedies differ, so the ledger carries the reading
> and a closed set of two refuses a third section added without somebody
> going and looking.
>
> **The guard reads rendered keys, which is honest only while the producer
> spells them.** That premise is a tripwire rather than a comment, and the
> evidence for it is live: driven through the fixture, `Filesystem` renders
> `['total_mb']` — a key `render_sections` never names and
> `_gather_filesystem` never returns. It arrived from the fixture. A
> rendered-keys assertion there would pin the fixture and pass over anything
> the producer did, which is the circularity the sibling's fixture premise
> exists to prevent, arriving one level down.
>
> **The retired half is empty by measurement and is not left as silence.**
> No field has ever left either ledgered section. A parametrised test over
> an empty mapping is green without running, so the retirement rules are
> driven at a **synthetic** pair as well — the detector is shown to reject a
> retirement that dates nothing and names nothing, so the shape is enforced
> before a real one lands.
>
> **Twelve mutations driven and all twelve land**, ten on exactly one test.
> **One was measured wrong before it was measured right**, which is the part
> worth carrying: the new file is *untracked*, so `git diff` verified
> nothing between mutations and the restore went unwitnessed — the run
> reported three reds across two sections where a re-run with the diff
> printed gives one, the history half. A mutation drive whose restore is not
> observable measures the previous mutation as often as the current one.
>
> **A restart was claimed and was not owed, by this sitting's own hand.**
> The mutation drive restored `sysadmin/briefing/data.py` with `cp`, which
> writes identical bytes and a **new mtime**, and the deploy claim compares
> file mtimes rather than commit times — so it reported the daemon stale for
> a file nothing had changed. Repaired by restoring the mtime from the last
> commit that touched it, not by restarting: `SNAG-SYSD-007` is what one of
> those costs.
>
> **Found and left, and it is red on a clean tree.**
> `tests/test_snag_claims.py::TestTheDuplicateIngestCheck::test_it_holds_against_the_live_table`
> was red before this sitting touched anything — verified by reverting both
> changes and re-running. It is a live-table check, so it went red by the
> passage of **time** rather than by an edit, and preflight runs no suite, so
> nobody would have seen it. `SNAG-LOG-014` claims **2** duplicate journal
> records and the check now measures **0**, across 629 `sysadmin.service`
> rows still inside the retention window — which is that entry's own
> prediction coming true on the day its `expires` claim named. Its closure
> is its own sitting, and so is that claim's: rewording a prediction is the
> easy half, and deciding what a red live check means for the entry behind
> it is not.

> **A practice is not a constraint, and this one was refuted 3 times in 6**
> (2026-09-15, Session 240, at the owner's direction to tell Alfred the
> producer is additive-only, and opening `SNAG-BRIEF-005`). The guarantee was
> **made true before it was sent**: `tests/test_briefing_sections_are_additive.py`
> is the guard, and estate message `eb7cbbf4-352f-49b5-907c-52035105fbb6`
> is the filing at Alfred.
>
> **The claim was false as an unconditional statement, and the first
> measurement of it was taken on the wrong population.** `docs/guides/` has
> said *"added, never renumbered or removed"* since 2026-08-06 and nothing
> enforced the producing half. A first walk read **9** commits and reported
> 2 removals in 3 transitions; the producer was `sysadmin/services/briefing.py`
> until the 2026-08-13 reshuffle, so plain `git log` **stops at the rename**
> and `--follow` gives **15**. The full history is **6** title-set transitions
> with a title leaving in **2** — the ADR-0005 migration, and an unannounced
> **rename** of `Overnight Log Summary` on 2026-08-24. A third departure the
> walk reports is its own artefact, described below. Both removals shipped
> green, because the titles live
> in scenario assertions the removing commit edits alongside the removal.
>
> **A removal now has exactly one quiet path left, and it is the one that is
> supposed to be taken.** The ledger's halves fail in opposite directions:
> dropping a title from `SERVED_TITLES` alone is caught because the producer
> still renders it, and dropping it from **both** halves is caught because a
> walk of the producer's own git history still holds the commit that served
> it. What survives is moving it to `RETIRED_TITLES` with the announcement
> that carried it — which is what *a change to a surface a repository
> publishes is announced by a filing at its measured readers* asks for anyway.
>
> **The ledger is in `tests/`, deliberately.** Nothing at runtime reads it, and
> a constant under `sysadmin/` with no runtime reader is precisely the shape
> Sessions 236, 237 and 238 spent themselves deleting. It also costs no
> restart, which is why the deploy claim is unmoved.
>
> **A reported removal turned out to be the instrument, and reading the diff
> is what said so.** Transition 2 of 6 shows `Weekly Project Review` leaving on
> 2026-08-06; the commit actually **parameterised** it —
> `"title": "Weekly Project Review"` became `"title": title`, the literal
> moving to the call site. The walk reads `{"title": <literal>}`, so a title
> built from a variable is invisible to it and its absence looks like a
> departure. Under-collection is the **safe** direction, because the history
> test asserts a *subset*, so a missed title can never redden it by accident —
> what it can do is fail to redden at all, which is `SNAG-BRIEF-005`. Both
> closures were refused: following the parameter re-implements Python's own
> binding across a file whose shape changed twice, and collecting every string
> literal makes the instrument read this module's own docstring, which names
> four retired titles by design.
>
> **Ten mutations driven and none passed green**, which is better than this
> repository's usual rate and the reason the pass is run. Seven land on
> exactly one test; three light two each and each is right to. **One premise
> had to be decoupled before it could be driven at all** — it asserted
> `len(rendered) == len(SERVED_TITLES)`, so it reddened whenever the producer
> dropped a section, a premise standing in front of its own subject and one
> mutation lighting two tests. It derives the fixture's keys from an `ast`
> walk of `render_sections` now, so it is about the fixture and nothing else.
>
> **The headline said 3 and the right answer is 2, and a third party is what
> settled it.** The walk reports three departures and the third is its own
> 2026-08-06 blind spot — which this block already called an artefact two
> paragraphs down, so the figure was refuted below itself, which is
> `SNAG-BRIEF-005`'s shape turned on its author. estate-manager measured the
> same history independently on 2026-09-14 and recorded `title_set_changed =
> 6, commits_removing_a_title = 2`: **agreement on the first figure, and their
> number right on the second.** Corrected here, in the guard, in
> [ADR-0014](../adr/0014-a-sample-cannot-be-both-pinnable-and-real.md) §9, and
> at Alfred as `202e3fa5-5854-428b-92d9-8582661a2abc`, the wrong count having
> gone out in a message about their own fixture's producer. Note which way the
> blind spot runs: it can **over-report a departure** as well as miss a title,
> and only the second is a gap in the guard — an over-report changes no
> assertion, since the title is still in the ledger from the commits that
> spelled it. What it costs is a reader.
>
> **A message was drafted, measured and refuted before it was sent.** The plan
> was to tell estate-manager that `monitorable-project.md` carries no
> additive-only rule. It does not — and `alfred-briefing-integration.md`
> states the task's sentence almost verbatim, sourced to `a8cace4`,
> **inherited from this repository on 2026-08-06**, the day Session 33 was
> requested. The roadmap task asking for it was discharged by its own sitting
> and stood unticked for **40 days**, kept open by two sweeps of the one
> document it names. estate-manager's ADR-0123 §5 is about that failure
> exactly — a refutation a few paragraphs away in the same governed section —
> so filing it would have been that failure returned to its author. Ticked
> instead. What was sent is the opposite:
> `9b8e6f91-6022-4874-97b2-e6d3472b9fc5`, telling them `estate-map.md`'s
> *"guarded by ... coordination"* line has aged now the producing half has an
> enforcement.
>
> **`SNAG-BRIEF-004` is closed by the message, and its shape-of-fix was one
> filing too many.** That entry costed the remedy as a filing about *Alfred's*
> document; what was owed was a filing about **our** producer that happens to
> make their sentence false, so the README correction is the closing clause of
> the additive-only message rather than an envelope of its own. Suite
> **4156 → 4170**, green; ruff and mypy clean; nothing under `sysadmin/`
> changed, so no restart is owed and all **15** ops claims read `ok`. The
> register holds 38 open and 0 owed.

> **A sample cannot be both pinnable and real** (2026-09-14, Session 239,
> discharging Session 238's handoff and opening `SNAG-BRIEF-004`).
> `docs/contracts/briefing_preview.sample.json` is **refused**, not
> deferred, by [ADR-0014](../adr/0014-a-sample-cannot-be-both-pinnable-and-real.md).
> Four Session 33 tasks standing since 2026-08-25 are closed by decision;
> two are untouched and one of those is not this repository's to do.
>
> **The refusal lands one step earlier than the estate's.** Their
> withdrawal (message `d29929d7`) says neither half of *their* comparison
> is testable. This says the artefact task 1 could commit and the artefact
> Alfred's fixture directory admits are **different artefacts**. Driven
> live read-only, `generate_briefing_data` called twice **1.1 s** apart
> against an unchanged database differs in **three** fields —
> `generated_at`, `period.to`, `facts.logs.measured_at` — so *"fails when
> it differs from the committed copy"* fails on the second call. Normalise
> those and the counts underneath are still live; freeze the database and
> the product is a hand-written example, which is the one thing ADR-0063
> §3a refuses.
>
> **The section set is weather, measured on our rows rather than their
> commits.** estate-manager measured the producer's **code** across 15
> commits, which is a proxy. Reconstructed from the three review tables
> against the 06:00 boundary, the presence triple took **five** distinct
> shapes across the last **30** mornings. Today is the fifteenth
> consecutive day at the full six — the most flattering morning in a month
> to take a sample, and the trap.
>
> **The consumer already absorbs what the sample was for.** Alfred's
> `normalise_type` degrades any unknown section type to `text` with the
> data kept, asserted by two tests as a requirement rather than enjoyed as
> an accident — so there is no section this producer can serve that Alfred
> cannot map. And its mapping assertion is derived from whatever payload
> it is handed, which makes it as incapable of failing against a published
> sample as against a stale capture. Publishing changes which file is
> asserted against itself.
>
> **Both of the estate's headline claims reproduce on this repository's
> own instruments**, re-taken rather than accepted: five of six sections
> sit behind an `if` in `render_sections`, and an AST walk of Alfred's
> `alfred/services/briefings.py` finds it reads `sections`, `facts` and
> `generated_at` and never `schema`, `period`, `alerts`, `summary` or
> `source` — **3** of **8**.
>
> **One catch is genuinely surrendered and says so.** Alfred's four-type
> union assertion could fire on a morning this box stopped serving a type.
> It is refused because it fires as a red test in Alfred caused by our
> weather, and a consumer's suite going red for a producer's data is worse
> than the manual refresh it replaces.
>
> **Nothing under `sysadmin/` changed, so no restart is owed and the suite
> is unmoved at 4156**, green; ruff and mypy clean. One line of test code
> did move, and it is the ADR count guard earning its keep: `docs/README.md`
> spells the count as a word — *"Fourteen records."* — and
> `test_the_stated_count_is_the_measured_one` reads it as a word on the
> stated reasoning that one *"goes stale exactly as a digit does"*. The
> fourteenth record is the first to need a word `NUMBER_WORDS` did not
> hold, so the map gained **one** entry rather than a spare range, which
> is what its own docstring asks for: a vocabulary *"only over the range
> these documents actually use"*. The residue is `SNAG-BRIEF-004`: Alfred's fixtures README
> still calls the sample *"blocked, not merely unbuilt"* and cites a
> blocker that no longer exists, and no message was filed to say so — put
> to the owner this sitting and declined, so it is recorded rather than
> absorbed. Estate message `d29929d7` is deliberately **left open**:
> nothing is owed to estate-manager, and the once-a-session inbox notice
> is a more durable reminder than a checkbox, which would publish itself
> to the board as this repository's next action. The register holds **38**
> open and 0 owed.
>
> **Two ops claims went red mid-sitting and neither was this sitting's
> doing.** `Estate port 3110 registry breach` and `Estate port 8110
> registry breach` opened at **20:20 UTC**, twenty minutes after the
> decision work began — Alfred's `nuxt dev` and `uvicorn --reload` behind
> an editor, at `warning` rather than the quiet rung because the sweep
> that would attribute them predates them. Both are declared flapping
> below rather than added to the pin, on the duty cycle the checker
> measures. They are `SNAG-ESTATE-009`'s first observed `warning` rows:
> that entry's own note records it had **never observed its own class**,
> and it has now. Claims read **15** of 15 `ok` — fifteen rather than
> thirteen because a flapping declaration is itself a claim, so declaring
> two added two.

> **A leaf can lose its reader to a refactor, and that is the shape this box
> has actually produced** (2026-09-14, Session 238, discharging Session 237's
> handoff). `dashboard_url` — the one `TrayConfig` leaf that sweep found
> unread one seam over — is **removed, all three halves**, and the walk that
> found it is standing: **19** leaves before, **18** after, none unread.
>
> **It had a reader and a commit took it away, which is the opposite of the
> four decided yesterday.** `git log -S` over 348 commits names six touching
> the string. `81b3bfb` wired it to `TrayApp._open_dashboard`, which called
> `webbrowser.open(url)` and fell back to `f"{api_url}/docs"`; `3f68448`
> (2026-02-13, *"add native dashboard"*) replaced that body with
> `self._dashboard.toggle_visibility()`. The **menu item survived and still
> works** — what went is the browser, so `webbrowser` is imported nowhere
> under `sysadmin_tray/` and a value in this leaf could reach no code at all.
> It outlived its mechanism by **seven months**.
>
> **The shipped value restated the fallback the deleted code supplied
> itself.** `config.yaml` set `http://127.0.0.1:8500/docs`, which is exactly
> what `_open_dashboard` synthesised when the leaf was unset — so the file
> was configuring nothing even while a reader existed.
>
> **Residue gets a standing guard after all, for the mirror of yesterday's
> reason.** Session 237 argued that a birth defect has no date and therefore
> needs a guard where residue needs a sweep. This is residue and it gets a
> guard because the two catch **opposite events**: those four never had a
> reader to lose, so that guard catches a leaf *arriving* unread, and this
> one catches a reader *leaving* — which is the commoner event and the only
> one of the two this box has demonstrated.
>
> **A tray setting has three halves and the third had no speaker, which
> only driving it said.** A key needs its `config.yaml` line, its
> `TRAY_SECTION_KEYS` entry *and* its field. Two were guarded already: a
> line with no entry is named by `tray_section_report` and reddens
> `test_every_shipped_key_is_read`, and a field with no reader is what the
> new guard catches. A line and an entry with **no field** were dropped
> without a word — `load_tray_config` copies the value into `kwargs` and
> the model discards it. **Fixed rather than filed**, because measuring it
> made the guard two assertions: **6** and **9** allowlist entries, **no
> orphan in either**, so it ships with an empty finding population and
> says so. It also corrected the sentence that was going to be written
> here. *`TrayConfig` sets no `model_config`* is false — pydantic puts one
> on every model; what `TrayConfig` does not set is **`extra`**, and the
> default is `ignore`. A claim read off the class rather than driven at it.
>
> **The note explaining the absence is weaker evidence than yesterday's, and
> the test says which.** Those removals left docstrings, and a docstring
> survives parsing as an `ast.Constant` — grep finds it, `attribute_reads`
> does not. This one is a plain **comment**, which the tokenizer discards
> outright: invisible to every AST instrument and visible only to a lexical
> one. So the test asserts an equality over `tokenize` — *every* occurrence
> of the name in the file is a comment — rather than restating the
> reachability claim one test above, which would be one fact with two
> speakers and unfalsifiable one-to-one.
>
> **Eight mutations driven; six land on exactly one test and the two that
> land on two are right to.** An unread leaf arriving, a reader appearing,
> the note deleted, an unread sub-config nested, and an orphan entry in
> either allowlist each redden exactly one. The
> walker crippled reddens **both** premises — one per guard, which is what a
> vacuity premise on a shared helper is for — and the original defect
> restored verbatim reddens the leaf guard **and** the comment equality,
> which is a defect two independent guards catch. Session 237's sharpening
> transferred: a nested model carrying an unread *leaf* reddens the leaf
> guard too, so the container control is one whose leaves all have readers.
>
> **The box's own vacuity checker caught the container half, and declaring
> it was the honest answer rather than deleting it.**
> `check-vacuous-guards.sh` reports a comprehension under `tests/` that
> turned **zero** times on a green suite, and this one cannot turn:
> `TrayConfig` is flat. It carries a `may-not-turn` declaration now, because
> the identical comprehension in the `AppConfig` sibling runs over **31**
> containers — the shape is witnessed turning, and what is nought here is
> the population rather than the reader. So *"empty population and says
> so"* had to be earned at the close rather than asserted in a docstring.
>
> **No restart is owed, and that is measured rather than assumed.** Nothing
> under `sysadmin/` changed — the daemon's import graph is untouched, so
> `check-ops-claims.sh`'s deploy claim is unmoved and the burst budget was
> never spent (`SNAG-SYSD-007`). The tray reads `config.yaml` at startup and
> nothing read this leaf, so the running tray is unaffected either way. All
> **thirteen** ops claims read `ok` — and thirteen is a *correction*, not a
> restatement: Session 237's block says fourteen, the marker population is
> byte-identical at that commit and at this one, and the figure was carried
> forward here before it was counted. `SNAG-ESTATE-012` is why nothing
> caught it — *"all fourteen ops claims read ok"* is prose with no pattern
> and no marker, so the checker that verifies every figure in this block
> cannot see a sentence about **itself**. A live specimen for an entry that
> had none.
> Suite **4150 → 4156**, green; ruff and mypy clean. No new SNAG id — the
> register holds 37 open and 0 owed.

> **A leaf with no reader is a property a test computes** (2026-09-14,
> Session 237, discharging Session 236's handoff). The four `AppConfig`
> leaves that sweep found with no reader under `sysadmin/` were read one
> at a time and **all four removed**, both halves each — and the one-off
> sweep became a standing guard over the whole field tree: **116** leaf
> names and **31** container names, none of them unread.
>
> **All four are birth defects rather than residue, and `git log -S` over
> 348 commits is what says so.** Every one entered in the **first commit**
> and no commit has ever added or removed a reader for any of them. That
> is a different animal from the block just trimmed, whose readers left
> with the projects domain on 2026-08-13 (ADR-0005). Residue arrives on a
> known date; a birth defect arrives whenever somebody declares ahead of
> wiring, which is why the guard is standing rather than a sweep.
>
> **The CPU pair inverted under measurement, and that is the finding.**
> Reading the code says CPU is sampled and never alarmed —
> `_check_thresholds` has no CPU branch — so the expected report was a
> blind spot. The live table refutes it: across **3,497** snapshots the
> median is **1.7 %**, **two** samples reach 90 %, both isolated, and the
> longest consecutive run is **one** five-minute sample against a declared
> ten. An empty population over 90 days, while `Unusual CPU usage` was
> raised **67** times, fires at 24–26 % and caught the 98.7 % spike at
> **7.2σ**. The pair was not a missing safeguard but the wrong one.
>
> **What is genuinely uncovered was filed, not kept as configuration.**
> `anomaly.py` skips a metric whose σ falls below `min_stdev`, so a box
> pegged at a steady 95 % is not merely un-alerted — CPU leaves the sweep
> entirely. That argument is on `ideas.md` with a trigger that re-opens it
> by a count; this box sits at σ **6.85** against a floor of 1.0. Keeping
> the leaves instead would have left a setting that reads as an armed
> alarm and arms nothing.
>
> **Each of the six new tests was uniquely falsified and the sixth
> mutation had to be sharpened.** The first container mutation added a
> model with an unread *leaf* too and reddened two tests, so it was
> replaced by one whose leaves all have readers. The container half ships
> with an **empty** finding population and says so — `ports_checked`'s
> rule — and a vacuity premise pins the walk, because a walker that
> stopped descending would sweep a handful of fields and report clean.
>
> **The commit that deletes the four names all four in prose.** `grep -c
> cpu_sustained sysadmin/` now returns **2** and `attribute_reads` returns
> **0**, because a docstring is an `ast.Constant` and a read is an
> `ast.Attribute` — `snag_claims.py`'s "the whole reason this is not three
> lines of `grep`", specimened by the change that removes them. A second
> instance the same sitting: `grep` ranked this block's own quoted
> checkbox first in `tasks.md` and the real parser does not, `_UNCHECKED_RE`
> being anchored at line start.
>
> Verified live rather than only in tests: `POST /api/sysadmin/reload`
> returns `unknown_keys: []`, `unwalkable_sections: []`,
> `requires_restart: []` — the file and the model agreeing on the running
> box, which a model-only deletion would have made loud. Suite **4144 →
> 4150**, green; ruff and mypy clean. Daemon restarted at
> 2026-09-14 18:19:50, `NRestarts=12`, `/health` 200; the budget was
> checked first and the 10-minute burst window held zero starts
> (`SNAG-SYSD-007`).

> **Both halves of a setting have to move, and they fail in opposite
> directions** (2026-09-14, Session 236, discharging Session 235's handoff
> and opening `SNAG-CFG-008`). `config.yaml`'s `agents.project_organiser`
> block is trimmed to the leaves that have readers. It held **13** parsed
> leaves across five nested models; it holds **2**. The agent left on
> 2026-08-13 (ADR-0005) and everything it reasoned with went with it —
> grade bands, TODO patterns, idle-nudge thresholds, branch-prune safety
> rails, the `estate.json` output contract — leaving configuration nothing
> could read, which is `SNAG-CFG-001`'s shape.
>
> **The key and the field had to be deleted together.** A key in the file
> with no field in the model is *loud*: `config_keys` walks `model_fields`
> and names the orphan in the lifespan and on every reload. A field with
> no key is *silent*: the value falls back to the model default, and for
> `enabled` that would have turned the file's recorded `false` into a
> parsed `true`. So trimming one side alone is not half the job in either
> direction — it is a no-op that reverses a decision.
>
> **The handoff's premise was right and its reader set was one short.**
> `projects_root` does have **seven** live readers, as it said. It also
> missed `discovery_depth`, which has **two** (`units/agent.py`, both
> handed to `load_registry`) and appears in **no** `config.yaml` — so a
> trim scoped to the *file*, which is how the next action was worded,
> cannot see it and would read its absence there as evidence it was dead.
> It survives, and it is not written into the file either: a value stated
> in two places is free to disagree with itself.
>
> **One of six falsifications passed against deliberately broken code**,
> which is the usual rate here and the reason the pass is run. Deleting
> `discovery_depth` from the model left all five new tests green —
> `attribute_reads` measures `units/agent.py`, which the deletion does not
> touch, and the reader-loop simply iterates one field fewer. A no-op
> mutation is not a control, so the test now asserts the declaration. The
> other five land: a restored key reddens 2, a restored unread field 1,
> `discovery_depth` written into the file 2 — and a restored **colliding**
> field stays green, which is `SNAG-CFG-008` rather than a miss.
>
> **A guard fired that was written to fire, and the number it wanted was
> not the number it guards.** `test_no_config_model_forbids_unknown_keys`
> asserts `models >= 37` with the message *"the module shrank; re-measure
> before trusting this"* — a **premise**, without which `strict == 0`
> passes vacuously over an emptied module. Deleting five models made it
> 32. Re-measured rather than nudged, and the claim it protects is
> untouched: the asymmetry is `0 of N` here against `4 of 4` in
> `services.yaml`, so what must not move is the **0** and the **4**.
>
> Verified live rather than only in tests: the restarted daemon logs
> `registry_loaded root=/home/gaddi/projects repositories=27`, and
> `POST /api/sysadmin/reload` returns `unknown_keys: []`,
> `unwalkable_sections: []`, `requires_restart: []` — the file and the
> model agreeing on the running box. Suite **4140 → 4144**, green; ruff
> and mypy clean. Daemon restarted at 2026-09-14 14:34:00,
> `NRestarts=11`, `/health` 200; the budget was checked first and the
> 10-minute burst window held zero starts (`SNAG-SYSD-007`).

> **Naming a closed entry is not proof the item is done — it was right three
> times in nine** (2026-09-14, Session 235, closing `SNAG-DOCS-031`). The one
> struck-through item in `docs/roadmap/tasks.md` is ticked, keeping the
> strikethrough and the *"Done above."*: the retirement a human could already
> read is now one the machine can. Driven at the reader either side rather
> than judged by eye — `count_unchecked` **74 → 66**, seven ticks and one box
> removed reconciling exactly, and **no** unchecked line in the document
> carries `~~`. `count_checked` reads **1460 → 1479**: the same seven plus the
> **twelve** `- [x]` bullets this sitting's own block is written as — stated
> that way because reading the delta as a tick count is the error corrected
> below. `first_unchecked_task` is
> **unmoved** at ``Next up → **`SNAG-CFG-007`…``, which is the correct
> outcome: the specimen sat below that open item, exactly as the entry said
> when it ranked itself P4 on reachability.
>
> **The nine candidates split four ways.** Five are discharged and ticked
> with a dated clause naming the closer — the raw-JSON signatures
> (`SNAG-LOG-008`, Session 116's `message_backfill.py`), the contended-default
> delegation (`SNAG-ESTATE-004`, fixed by estate-manager), ImbaBots' undated
> handoff (`SNAG-PROJ-013`), the `count_open_snags` miscount
> (`SNAG-ROADMAP-002`, fixed by estate-manager) and the sustained-fault raise
> side (`SNAG-AGENT-006`, `_raise_judged`). A sixth — the 547,814 unresolved
> kernel rows — is ticked on its own evidence: that family holds **607,148**
> rows and **0** unresolved. **Two stay open and one lost its checkbox.**
> Every tick was verified at the thing rather than at the register.
>
> **One of the two left open refutes its own stated remedy, and only
> replaying the table could say so.** *"Page-1 churn can re-notify a standing
> alert"* routes its fix to the volume, and that volume fix landed on
> 2026-08-12. Replaying `created_at`/`resolved_at` as a running open-row
> count, the table held **95** unresolved rows at once on **2026-08-13** — the
> day *after* — and stayed over the 50-row page for **2 h 41 m**. Clear since
> (max **34** to 08-29, **19** in the last seven days), but clear is a
> property of the fault load, not of the code. **The other's premise is half
> wrong and `config.yaml` already said so**: `agents.project_organiser`'s
> `projects_root` has **seven** live readers, so a trim can take the other
> leaves and not the block.
>
> **The ninth lost its checkbox rather than being ticked or deleted** —
> Session 234's treatment applied a second time. *"The retirement checklist …
> not this repository's to enforce"* is a decision that stands; re-read at the
> owner before saying so, and estate-manager has recorded retirement material
> of its own (their ADR-0136) without adopting a checklist.
>
> **No Python changed**, so no restart is owed, the suite is unmoved at 4140
> and no test was added — the entry's refusal of a check stands, and is
> stronger than when it was written: the mechanisable proxy became true at the
> moment of the tick, and the half that did the work was reading nine items.

> **A retirement is recorded in the box, not in the prose** (2026-09-14,
> Session 234, discharging Session 233's handoff and opening
> `SNAG-DOCS-031`). The four stale unchecked items at the top of
> `docs/roadmap/tasks.md` are cleared, and the reader was driven either side
> because "stale item" is a claim about what another repository publishes.
> estate-manager's `first_unchecked_task` returned
> ``Left open → **`SNAG-DOCS-014`…`` — closed 2026-09-10, under a heading
> carrying no session identity — and now returns
> ``Next up → **`SNAG-CFG-007`'s stated trigger has fired.**``, which is open
> and startable. `count_unchecked` **78 → 74**, `count_checked` **1446 →
> 1449**: three ticks and one box removed, reconciling exactly.
> *(Corrected 2026-09-14 by Session 235: the reader says `count_checked`
> **1446 → 1460**. The 14 are 3 ticks plus **11** `- [x]` narrative bullets in
> the session block that commit added, so the conclusion — no clobber — holds
> and the arithmetic was taken over the wrong population. A session block
> written as checked items is part of the census it reports.)*
>
> **Three were ticked with a dated closing clause and none deleted** —
> `SNAG-DOCS-014` fixed by Session 210, `-016` decided by Session 214 as
> ADR-0011, `-015` fixed by Session 216 — because deleting loses what a
> sitting deliberately left. **The fourth was neither**: *"the test count and
> the two Markdown line counts are deliberately not pinned"* records a
> decision that stands, so a tick would assert work done and a deletion would
> lose the decision; the **checkbox** came off and the bullet stayed.
>
> **The document already carried its own refutation one section above.** The
> four sit under Session 209's *Left open*, and Session 210 — which fixed the
> first of them — is the block immediately above it.
>
> **The durable half is an idiom, filed as `SNAG-DOCS-031` and deliberately
> not fixed here.** One item was retired by a strikethrough, which
> `first_unchecked_task` cannot see: driven at a document built from that one
> line it returns the item *with the `~~` markup intact*. **Tick the box,
> never strike the text.** Left because this sitting's declared scope was four
> named items, and it is not reachable today. Nine further items name only
> closed entries and are filed as a **population needing a reading each**,
> never as a count of defects. The census was reconciled at the consumer's
> key first: a hand-written `^- \[ \]` found 72 where `count_unchecked` finds
> **74**, their regex admitting leading whitespace and a `*` bullet.
>
> **No code changed**, so no restart is owed, the suite is unmoved and no test
> was added.

> **An absent reset at the failure instant is not an absent cause**
> (2026-09-14, Session 233, discharging the scheduled reading due today and
> closing `SNAG-SCHED-004` **into** `SNAG-GPU-001`). All three weekly review
> tables took the LLM this morning — health 05:00, log 05:15, disk 05:45 — so
> the entry's own rule closes it and the **slot** hypothesis it was ranked on
> is refuted. The disjunction is not what closed it: the two mornings ran
> different kernels, every `VRAM is lost` line in the retained journal belongs
> to the older one, and there have been none for 7.6 days — so *"all three
> true"* is equally consistent with the reset population having stopped. What
> refutes the slot is the inference itself, **570.18 ms** against a server
> unrestarted since boot, because no cold start existed to observe.
>
> **The cause was measured one entry over a week ago and nobody joined them.**
> `SNAG-GPU-001` already held it: the inference server reported `ok` for 99
> consecutive checks across 8 h 17 m while holding a context two resets old,
> and the 05:00 health review's prompt was the first chat completion of that
> process's life — which threw `vk::DeviceLostError` on submit and took the
> server down with it. **Both written sharpenings inverted their own
> evidence**, and one sitting wrote both readings of a single fact: Session 220
> read *"no reset since 2026-09-06 20:43:01"* correctly and forward on
> `SNAG-GPU-001`, and on `SNAG-SCHED-004` read the same observation as
> *excluding* the poisoned-context cause. ADR-0007's predicate wants the reset
> **between** the context's creation and the submit, so that observation
> satisfies the condition rather than refuting it. Session 224 inverted in the
> same direction, taking the estate's 05:30 success as independent of a restart
> our own crash had caused.
>
> One recorded mystery fell out for free, and the error was attribution rather
> than arithmetic: the `wait_seconds` figure the entry deferred as *"the
> estate's field on the estate's surface"* is `review_lease_budget` in
> `sysadmin/core/gpu_lease.py` — one deadline less each dispatch instant, all
> three values reproducing to the second. The `SNAG-GPU-001` rank was
> deliberately **not** lowered: a population that went quiet across a kernel
> change is not a mechanism that was fixed, and that reader has still never
> fired on real data.

> **A published key is necessary for a project-keyed reader and was
> never sufficient** (2026-09-14, Session 232, deciding estate message
> `a9ee6305` and recording it as
> [ADR-0013](../adr/0013-a-published-key-is-necessary-and-was-never-sufficient.md),
> answered as `0252530b-92c0-4516-80b9-94299a37732b`). estate-manager
> re-took this repository's scoping census on all 1,666 stored findings
> across 430 runs and refuted its conclusion: `ports` publishes
> `detail.project` on **803 of 929**, and on 100 % of every code with a
> claimant to name. The measurement is accepted; the widening is
> **refused**, and `scripts/check-estate-docs.sh` still reads `docs`
> alone.
> **The instrument aged faster than the conclusion**: the block being
> corrected read `ports  4 findings, 3` on 2026-09-12 and the same walker
> reads **6 sites, 4** two days later, their ADR-0166 and ADR-0168 having
> landed in between, with `docs` moving 7 → 9 in the same window. So the
> census is retired rather than refreshed and a property replaces it.
> **The property is that a project-keyed reader over `ports` is wrong in
> both directions at once, and both directions have filed nothing** —
> invisible to their `GROUP BY` over `audit_findings` and to ours over
> `Finding(` alike. `claimed_by_an_unregistered_tree` is `breach` **and**
> carries the key, and `JUDGED_AUDIT_CHECKS[ports]` is `breach`, so it
> already arrives hourly as an alert the tray speaks;
> `claimed_by_more_than_one_row` names its claimants in
> `detail.rows[].project` and would be read blind. Their own sentence is
> quantified over findings *ever filed* and the second sits outside it,
> so no correction is owed them.
> **A restart was owed and the reason is this sitting's own tooling, not
> a change.** The mutation harness restored `sysadmin/estate/judgements.py`
> with `cp`, which rewrote its mtime with **identical bytes** and
> destroyed the evidence the deploy check reads; the original could not
> be recovered — the `.pyc` header turned out to reflect this sitting's
> own `touch` rather than corroborate it — and inventing a plausible
> instant to make the check green was refused. The restart re-establishes
> the invariant rather than shipping anything: `git diff HEAD` on that
> file is empty. Daemon restarted at 2026-09-14 10:20:38,
> `NRestarts=10`, `/health` 200; the budget was checked first, the
> previous restart being eleven hours outside the 10-minute burst window
> (`SNAG-SYSD-007`).

> **Five of the twelve restatements were live and seven were already
> history** (2026-09-13, Session 231, closing `SNAG-DOCS-030`). The entry
> asked for nine sentences restating the estate's check total to be
> retired or re-derived one at a time, deciding per site whether the
> count carries an argument that needs a denominator.
> **The class is fourteen, and this sitting got the number wrong twice
> before getting it right.** The entry listed *files* and assumed one
> sentence each; `docs/roadmap/snag_list.md` carries **four** and
> `tests/test_estate_judgements.py` **two**, which makes twelve.
> **Twelve was also wrong, for this class's own recurring reason**: the
> sweep ran `grep --include="*.py" --include="*.md"`, a population
> chosen by habit and never driven, so it could not see
> `scripts/check-estate-docs.sh` or a JSON fixture's provenance note.
> **Three sittings running have asserted a count of this class instead
> of driving one** — `SNAG-DOCS-029`'s *"exactly one place"*, the
> entry's *nine*, and this fix's *twelve* — each refuted by one command.
> `SNAG-PORT-007`'s rule holds, and the correction to it is that *shape*
> includes which file types the sweep is allowed to look at.
> **The split the entry does not draw is what decided the work.** Five
> are live claims in code and test docstrings, which assert the current
> state and go stale silently; **nine** are dated records — an ADR's
> evidence, a session block, four fixed-snag measurements, a shell
> script's reason block and a fixture provenance note. A fourteenth
> check falsifies the five and leaves the nine **correct**, because
> `SNAG-DOCS-027`'s convention already makes a stamped measurement
> un-driftable. Only the five were touched; each survivor was checked to
> carry a date rather than assumed to, and the fixture note is the
> strongest form of it — it says the payload beside it holds thirteen
> checks and both scenarios it describes do, so it is self-verifying
> against its own artefact.
> **Exactly one of the five was carrying a proportion, and the
> denominator it needs is already served live.** `judgements.py`'s
> `ERRORED_REASONS_LISTED` comment argued *"ten at once is the audit
> failing"* — a claim about proportion that reads as nothing without a
> total. Eight hundred lines below, the message that constant caps opens
> `{errored} of {checks_run}`, read off the payload. So the comment was
> restating statically what runtime already supplies to the only reader
> who needs it, and re-deriving at import time — the entry's own refusal
> — would have made a docstring depend on 8400 being up.
> **The other four needed no denominator at all, for three different
> reasons.** Two said *"eleven of thirteen are excluded"* where the
> argument is that admission is per check and by ADR — the excluded count
> is the cardinality less two, so it says what *every other* already
> says. One is a test whose assertion never reads the figure, which is
> why retiring it costs the test nothing. The fourth claimed **totality**
> — `docs` is *"the only one of estate-manager's thirteen check
> modules"* — and **the only one** is already total, so the cardinal
> added nothing the word did not carry; the per-check figures beside it
> stay, each stamped with the day it was taken.
> **Both figures were verified true before being retired**, which is what
> keeps this P4 rather than a staleness bug: `last_audit.checks_run`
> reads **13** live, and an `ast`-free sweep of the estate's
> `audit/checks/` finds **10** modules with an error arm — `consumers`,
> `readers` and `seams` have none. Retired while still true, which is the
> distinction from `SNAG-DOCS-029` and is stated at each site.
> **The residue is a second foreign cardinality and it is not a new
> entry.** *"the hook entries binding all thirteen"* restates the
> estate's **repository** count at three sites — `judgements.py`, and
> ADR-0006 twice — and every one is inside a dated frame or attributed to
> the producer in the same clause, which is the treatment just endorsed
> for the seven survivors. Staleness could not be established here and
> the attempt is recorded rather than the guess: the estate's overview
> publishes **27** scanned projects and no status field, a different
> population from the one their hooks bind.
> **No guard, the entry's refusal inherited with its measurement.** The
> narrow mechanisable option — read `checks_run` live and refuse a tree
> whose restatements disagree — fails closed on a dead 8400 and answers
> the same way either side of a fix that removes the restatements, which
> is `check_review_schedule_unread`'s defect.
> **A restart was owed and paid once**, `judgements.py` being in the
> daemon's import graph although the edit is comment-only, so its
> observable effect is **nil by construction** rather than by
> measurement. Daemon restarted
> at `NRestarts=9`, `/health` 200 (the instant is dropped, this block
> being superseded by the one above — `ops_claims` rule 2's convention for
> a claim two blocks would otherwise state two ways).
> **Paid twice**: the sweep found two more
> sites after the first restart, so the home's own count had to be
> corrected — the budget was re-checked before the second rather than
> assumed, `SNAG-SYSD-007`.

> **A count of another repository's checks was retired rather than
> refreshed, and the entry named three sentences where the class had
> ten** (2026-09-13, Session 230, closing `SNAG-DOCS-029`; nothing under
> `sysadmin/` was touched, so **no restart is owed** and the ops-claims
> deploy check says so itself).
> Three sentences stated the estate's August audit vocabulary in the
> present tense — *"all four estate checks emit `breach`"*, *"`warn` is
> `claimed_but_silent`"* — and one of them was a summary of an ADR
> written partly to retire it. **The remedy was structural, not
> arithmetic**: a corrected count ages the next time the estate adds a
> check, so each sentence now carries the qualitative fact its argument
> actually needed. *"All four checks emit `breach`"* becomes *"`ports`
> does not have `breach` to itself"*, which is the minimal claim a
> severity-filter refusal requires and cannot be off by a number.
> **The class was swept by shape rather than trusted from the entry**,
> `SNAG-PORT-007`'s rule applied to the entry that recorded it: **ten**
> sites in three sub-classes, not three, and the third sub-class —
> *"`unclaimed_listener` is the only ports breach"* — was already
> **false** and unrecorded. Re-measured off their source rather than
> their database: **8 of 13** check modules can emit `breach`, so every
> consequence the original sentence named survives it — `collation`,
> `pointers` and `seams` all still breach-capable. What aged was the
> premise and never the argument.
> **The tenth site was on an open entry and was load-bearing.**
> `SNAG-ESTATE-006`'s *Cost today: none* rested on *"`unclaimed_listener`
> is the only ports breach, so nothing is ambiguous"*. With two breach
> codes that is false, so the cost was re-derived rather than re-worded —
> it survives, on rule 4 keeping the code out of the title by design
> rather than on a count that expired.
> **The correction to `test_two_findings_for_one_port_raise_one_row` runs
> opposite to the obvious one.** A second breach code landed and the fork
> is *still* unreachable by code, because the two partition the ports —
> one filed only for a port no row claims, the other only for a port some
> row does. The reachable path is two registry **rows**, which nobody had
> named.
> **The fix asserted a property nobody had measured, and measuring it
> opened `SNAG-DOCS-030`.** All four rewrites first read *"the figure is
> quoted in exactly one place"*; counting found **nine** restatements of
> today's total, **two inside `judgements.py` itself**. Corrected before
> it shipped — this register's own recurring failure, caught inside the
> fix for a sentence that had it.
> **The guard the entry proposed was driven before being refused**:
> 148 raw hits over 327 files, **47 %** precision after a context filter,
> and every in-class survivor is history — including the dated
> corrections this sitting wrote, because `SNAG-DOCS-027`'s convention
> keeps a retired claim verbatim beside its date. A lexical guard would
> fire on the convention that makes staleness legible.

> **The aside placed an overlap in the future that was already on four
> ports** (2026-09-13, Session 229, closing `SNAG-PORT-007` and estate
> message `84d72698`).
> `JUDGED_AUDIT_SEVERITY`'s docstring excludes `claimed_but_silent`
> because availability already has an owner here — `services.yaml` plus
> the `% unreachable` family — and then called it *"luck rather than
> design"* that the one live `warn` (port 3300) does not overlap, the
> overlap arriving *"on the day that unit ships"*. estate-manager
> measured their own 430 audit runs by presence **streak** rather than by
> finding — the unit an alert family raises in, since this judge raises
> on appearance and resolves on clearance: **27** raise-events across 7
> ports, 26 self-clearing, and **23 of the 27 on ports `services.yaml`
> already carries a `port:` entry for** — 8080, 8500, 3100, 3200.
> **The correction carries their cause and not their headline**, which
> is what the entry asked for and is why it needed their driver rather
> than their message: **19 of the 27 are port 8080 alone**, whose streak
> *starts* are identical to all 19 of `8083:dormant_but_listening`'s —
> one event, the estate's own GPU arbiter stopping `venture-chat.service`
> (:8080) and starting `venture-chat-large.service` (:8083) on a lease
> grant and reversing it on release. A rewrite saying *27* would have
> restated a number whose population mixes causes.
> **The argument is untouched and only the aside moved.** Excluding an
> availability finding because availability has an owner is the
> second-owner rule, and it holds whether or not the two populations
> meet — indeed an overlap is the **reason** to exclude rather than a
> reason to reconsider. Nothing changes about what is judged, and their
> ADR-0170 refuses to send the recommendation this measurement was taken
> for, its own evidence being against it.
> **The entry named one site and the class had three**: the docstring,
> `CLAUDE.md`'s condensed copy of the same rule, and this dashboard's
> Session 26b-A history block. Each keeps its original dated rather than
> deleted. The streak arithmetic is **not** re-taken here — no
> application reads another application's database — and the local half
> was checked instead: `GET :8400/api/audit/findings` still shows 3300 as
> the one live `warn`, `services.yaml` does not carry it, and all four
> ports they name are in this repository's declared set.
> **A restart was owed and paid once**, `judgements.py` being in the
> daemon's import graph although the edit is comment-only, so its
> observable effect is **nil by construction** rather than by
> measurement. Daemon restarted
> at **21:40:59** that day, `NRestarts=7`, `/health` 200.

> **The marker came off the published line, and the pin can only see one
> of three mistakes** (2026-09-13, Session 228, closing `SNAG-DOCS-028`;
> the one module edited is outside the daemon's import graph, so no
> restart is owed and the ops-claims deploy check says so itself).
> estate ADR-0167 made the action the board publishes the line **without**
> its optional end-anchored `*(For: session)*` marker, which now reaches
> the board as `next_action_for` and `next_action_estimate_minutes`.
> `snag_claims.next_action_line` documents itself as *"the line the estate
> board publishes"* and returned the raw line, so it was wrong by its own
> docstring from the moment their ADR landed — **marker or no marker**.
> Writing one merely made the disagreement observable, which is the
> reverse of the obvious reading that a new syntax broke a guard.
> **The strip mirrors their *loose* pattern rather than their strict
> one.** `read_next_action_line` finds a marker with the loose form and
> cuts the text with it, using the strict form only to decide
> `who`/`estimate_minutes` and to set `marker_readable` — so a
> present-but-unreadable marker comes **off** the published line, and a
> strict mirror would diverge on exactly the case where the author got
> the syntax wrong. **The pattern captures nothing**, which is the
> entry's *"must not publish `who` or `estimate_minutes`"* made
> structural: theirs has a group because it reads the marker, and a
> zero-group pattern cannot.
> **Which guard can see which mistake was measured, and that is the
> sitting's finding.** Driven against the live line and two forgeries: a
> **missing strip** is caught by any marked document — the byte-equality
> pin, once a marker is written; an **unanchored** strip is caught by
> today's live line *by accident*, because a sentence about the marker
> quotes it mid-line inside backticks and tomorrow's will not; a
> **strict mirror** is caught by an unreadable marker and by nothing
> else, which no real author writes. One mutation is the pin's, one is
> today's luck, one is only ever synthetic — so five tests sit beside a
> pin that was already the falsification. Four mutations driven and each
> lands on its intended test.
> **The floor test is reddened by none of them and its docstring says
> so** rather than claiming a control it is not: *an unmarked line is
> returned byte-identical* is the case every green run before today
> already covered, and an unanchored pattern cannot eat a `*(For:` an
> unmarked line does not carry.
> **A marker is written on this sitting's own next action**, which is
> what the entry asked for and closes the one cost it filed — the board
> stops publishing `next_action_for: null` for this repository. It stays
> *optional* by the announcement that introduced it, so the pin's power
> to see a missing strip belongs to whatever the current sitting happened
> to write, which is why the synthetic five are not redundant with it.

> **A flag was pinned where the claim is about a verb** (2026-09-13,
> Session 227, re-keying `SNAG-PORT-006`'s red pin and correcting the
> twelve sentences the two estate messages made false).
> estate-manager's `4c3ad2d` changed `live_listeners()` to
> `ss -H -ltnp`, reddening a pin that asserted the literal
> `'["ss", "-H", "-tln"]'` in their source. It fired correctly and its
> stated conclusion does not follow: the docstring's condition is a
> **conjunction** — *adds `-p`* **and** *attributes ports itself* — and
> only the first limb landed.
> **The replacement asks what they do with the pid.**
> `tests/test_estate_port_join_live.py` blinds their `directory_of`
> reader and requires every attribution to collapse to `no_directory`,
> driven at **both** `attribute` and `run_check`, because a unit route
> added above the join is invisible one layer down. Six tests in 0.20 s.
> **A green collapse is evidence only where the two joins can disagree**,
> so that is a premise rather than a hope: measured 2026-09-13, **21 of
> the 29** ports `ss` names a process for have a unit from our cgroup
> read and no registry tree from their directory read — 8080, 8081, 8082
> and 8384 among them, every one a service whose `WorkingDirectory` is
> `/` or `$HOME`. The other eight resolve under both and name different
> vocabularies: `alfred-frontend.service` against the registry id
> `alfred`.
> **Four mutations driven and all four land on the right test.** The
> first models the landed fix — a producer whose `attribute` falls back
> to our cgroup read — and it reddens both altitudes **independently**,
> 21 surviving outcomes at `attribute` and 14 resolved at `run_check`.
> A stand-in that stops modelling the fix reddens only the control; a box
> where the joins agree reddens only the separator.
> **The message named three sentences and the class has twelve**, across
> six files and two claims — *they run `ss` without `-p`* (five sites)
> and *`claimed_ports` is a set, so duplicates are invisible* (seven).
> Two of the twelve reach served payloads: `duplicate_claim`'s summary
> under `GET /api/sysadmin/ports` and its recommendation action under
> `GET /api/units/actions`, both of which told a reader the estate
> *cannot* see a duplicate row. It can, since their ADR-0168, and files
> it at `warn` — which `JUDGED_AUDIT_CHECKS[PORTS_CHECK] = "breach"` does
> not read, so **the surface is unmoved and only its reason changed**.
> Every corrected sentence keeps its original dated rather than deleted,
> which is what makes a stale claim legible as history.
> **A restart was owed and paid once**, three daemon modules being
> edited, two of them carrying strings a route serves. Daemon restarted
> at **20:06:22** that day, `NRestarts=6`, `/health` 200. Its observable effect is nil today and
> that is measured rather than assumed: the duplicate-row population is
> **zero** across all 25 revisions of the estate's table, so no reader
> sees either corrected string until the first duplicate lands.

> **The two computable claims are computed, and the suite went red for a
> producer** (2026-09-13, Session 226, building `SNAG-DOCS-027`'s guard;
> no production code changed and `services.yaml` is byte-identical, so no
> reload and no restart are owed).
> `tests/test_services_yaml_live.py` is six tests in 0.16 s: **every unit
> the file declares is installed** — 31 entries, `LoadState=loaded` with
> a non-empty `UnitFileState`, which is the `estate-broker-provision`
> claim generalised from one sentence to the whole file — and **the
> standalone oneshots are exactly the pair named**, computed as
> `Type=oneshot` + `RemainAfterExit=yes` + nothing in `TriggeredBy` over
> the file's own nine `kind: systemd` entries. The nine is **not** pinned:
> a count is arithmetic nobody can check.
> **The reading that reordered the guard is that systemd cannot tell the
> two apart.** `systemctl show` answers `TriggeredBy=''` for a unit that
> does not exist, byte-identical to a real unit no timer triggers — so
> *"nothing folds this oneshot"* is only a measurement on a unit already
> shown to be installed, and the installedness sweep is a **premise** of
> the uniqueness half rather than a sibling of it. The premise measures
> that indistinguishability instead of asserting it.
> **Named `_live` against the entry's own specification**, because
> `tests/test_live_drive_premises.py` builds its population from the
> `test_*_live.py` glob and requires a marked premise of every member;
> taking the specified name would have discharged that rule by filename.
> Driven, not assumed — commenting the marker out reddens it.
> **Nine mutations driven and all nine land**, one of them the
> pre-2026-09-13 sentence restored verbatim. The one limb with an empty
> population here — a triggered `oneshot` + `RemainAfterExit=yes` unit —
> was given a real specimen with `systemd-run --user --on-active` rather
> than left unexercised, because a no-op mutation is not a control. Both
> probes were removed and the box carries no residue.
> **`SNAG-PORT-006` was opened by running the suite, not by reading a
> diff — there is no diff.** estate-manager's `4c3ad2d` today changed
> `live_listeners()` to `ss -H -ltnp`, reddening the pin that watches
> their invocation. It fired correctly and **its stated conclusion does
> not follow**: the docstring's condition is a conjunction — *adds `-p`*
> **and** *attributes ports itself* — and their `working_directory()`
> resolves `/proc/<pid>/cwd` to a registry **tree**, refusing unit
> attribution in writing (their ADR-0166 §4). What was pinned is a noun
> where the claim is about a verb, so what is owed is an instrument and
> not a decision about the module.
> **No friction was filed, and checking is why.** Message `16d3a757`
> carries *"`ss` now runs with `-p`"* under the heading **WHAT DID NOT
> CHANGE**, beside *"The claimant comparison … is not made here; that is
> your `wrong_project`"*. The estate announced at its measured reader; a
> message claiming otherwise would have been false.

> **The class turned out not to require a true day** (2026-09-13,
> Session 225, sweeping `services.yaml` for the shape Session 224
> corrected in one place and opening `SNAG-DOCS-027`; no Python changed
> and the parsed document is byte-identical, so no reload and no restart
> are owed).
> The handoff named two members of the class and defined it as *"true the
> day it is written and silently false afterwards"*. **There are five,
> and one of them refutes the definition.** All 19 measurable claims in
> the file were swept comment-by-comment rather than by grep — which was
> necessary, because three of the five carry no *not yet* / *upcoming* /
> *until* token at all.
> **Both named members were confirmed and dated.** *"The unit is not yet
> installed and this check will rightly complain"* was written 2026-08-11
> and the unit's enablement symlink is dated 2026-08-12 08:56 with its
> first journal line at 08:56:34 — **false for 32 days**, and the
> sentence had named its own expiry condition. *"That judging is this
> repository's own upcoming task"* was written 2026-08-12 and
> `judge_queue_invariants` landed 2026-08-13 — **false for 31 days**,
> while `estate_judge` read the surface hourly throughout.
> **The member that inverts the class is `ethernet-optimise`'s.** *"This
> is the one oneshot on the box with no timer that is still monitorable"*
> was written 2026-08-15, and `estate-broker-provision.service` — same
> `Type=oneshot`, same `RemainAfterExit=yes`, no timer, checked
> `kind: systemd` — had been 250 lines above it since 2026-08-11. So
> being true at birth is not what the class turns on; **nothing
> re-reading the sentence** is, and a uniqueness claim is its worst case
> because what falsifies it is an edit elsewhere in the same file.
> **A lexical guard is refused and this sitting's own corrections are the
> argument** — each preserves its original as *"this entry read … until
> 2026-09-13"*, the phrasing an *until* ban would redden, and none of the
> three untokened members would be caught. **But two of the five are
> computable with no marker at all, because the file is its own
> population**: the uniqueness partition over this file's `kind: systemd`
> entries, and `UnitFileState` on a unit the same entry declares.
> `ops_claims.py`'s marker machinery exists because `STATUS.md` has no
> declared subject; here every claim of this shape sits beside the unit
> name it is about.
> **The 14 that hold were measured and printed**, because a sweep that
> reports only its hits cannot be told from one that looked at nothing —
> Alfred's two 404s, sports-analyser on 8200 and 3200, no port attributed
> to `deadlock-api-ingest.service`, the sweep's two disabled-deadlock
> `host` findings, `alfred-career-mail.service` still `static`,
> `alfred-evaluate-frequent.timer` still the highest-cadence **active**
> timer at 288/day, and Session 224's own three-journal claim still at 0
> above INFO. The Alfred header's *"Four services"* against **seven** is
> **dated rather than rescaled**, knowingly trading this class for
> `SNAG-DOCS-026`'s, and 8080's *"should move to 83xx"* is left alone
> because it restates estate-manager's recommendation and the registry
> names 8301.
> Entries carrying no check **12 → 14**, which is the advisory this
> register already reports and not a regression: the guard is owed as a
> test rather than a check, because what one would drive asserts the
> **fix**.
> **A second entry was opened by writing this sitting's own handoff
> line** (`SNAG-DOCS-028`). estate message `c6f473f9` announced the
> handoff shape's optional `*(For: session)*` marker; writing it reddens
> the byte-equality pin between `snag_claims.next_action_line` and the
> producer's parser, because ADR-0167 made the published action the line
> **without** its marker and our reader still returns the raw line.
> Measured at their parser, the marker reads back as `marker='session'`
> with `who` populated, so **the board half works and the residue is
> local** — `next_action_line` is wrong by its own docstring whether a
> marker is present or not, and the marker only makes it observable. The
> marker was dropped rather than left red; the cost is one null
> `next_action_for`, which is the field the announcement was about. The
> pin earned its own stated design: byte equality rather than comparing
> the ids the readers name, *"because a set of ids stays equal through a
> divergence that changed the sentence"*.

> **The gate was asking the wrong journals** (2026-09-13, Session 224,
> settling `ideas.md`'s top entry and **building it the same day**; the
> register was not touched and no Python changed — the whole runtime
> change is three `log:` blocks in `services.yaml`, installed by SIGHUP
> reload with `requires_restart: []`).
> Session 223 narrowed that entry to a witness — one non-INFO record from
> the estate's three timer units, carrying a `<N>` — and offered two ways
> on: defer until one exists, or ask estate-manager. **Neither, because
> the witness existed and was never owed from those three.** ADR-0079's
> prefix is a property of the estate's shared `configure_logging`, which
> all four of their entry points call, and `resolve_format` picks the
> prefixing formatter by a **tty test**, so every unit under systemd
> takes the same branch.
> **It was in this repository's own database.** `estate-manager-api.service`
> has carried `format: json` since 2026-08-31, and `log_entries` holds
> rows at `PRIORITY=4` and `PRIORITY=3` through that formatter, the
> earliest the same day — so asking would have been friction we
> manufactured.
> **The premise that was false is the transferable half.** A prefix is
> *not* observable only above INFO: `MESSAGE`'s first byte is a second
> observable, and no record in the three journals begins with a literal
> `<N>`, which excludes `SyslogLevelPrefix=no` and leaves journald having
> consumed it. Measured on the box, with the format boundary in all three
> journals matching the producer's own commit on a clean tree.
> **What remains is only the population, and it is thinner than it
> looked** — post-ADR runs are 27, 15 and 2, the review having fired once
> under the new formatter — but *reachable and untriggered* rather than
> structurally empty, their three paths carrying the two warning records
> ADR-0075 names. The oneshot/timer worry dissolved: `LogRef.unit` already
> overrides the inherited unit.
> The cause of three derivations was a claim stated twice — a
> `services.yaml` comment asserting the prefix had *"no witness here
> either"*, false within hours of being written and uncorrected for
> thirteen days. Corrected in place, original kept as history.
> **Built and verified live.** The three entries are `kind: timer` and
> their journals belong to the `.service`, so each block names its unit
> explicitly through `LogRef.unit` — necessary rather than tidy, since
> the three timer journals carry 16 records each and **zero** written by
> anything but systemd, so inheriting the unit would have ingested
> nothing and reported clean. Driven at the real reader afterwards: **0**
> entries at the declared `warning` filter and **414 / 500 / 239** one
> rung down at `info`, which is what makes the zero
> *zero-because-clean* rather than zero-because-blind, and the `json`
> declaration unwraps live — `message` reads
> `weekly_project_review_generated` where `raw_line` keeps the envelope.

> **The argument was about the remedy and the obstacle was the operand**
> (2026-09-13, Session 223, answering estate message `11cf5113` and
> opening `SNAG-PORT-005`; [ADR-0012](../adr/0012-a-transient-holder-has-no-project.md)).
> estate-manager bound `127.0.0.1:3300` — the port their registry gives
> to `venture-assistant` — from `~/projects/web/portfolionew` inside a VS
> Code scope, watched `judge_ports` file **zero** findings, and asked
> whether `wrong_project` should read `transient_ports` the way
> `reading()` already does, on the grounds that the exclusion is right
> for the two families *whose remedies name a unit* and this one's does
> not. **No, and the argument does not reach the obstacle**:
> `wrong_project` compares the *project owning the unit*, so it has a
> unit in its question even though it has none in its answer.
> **The proposed fix is inert, and structurally so.** `unit_projects`
> comes from `discover_units`, which admits `.service`/`.timer`
> **files**; systemd writes no persistent scope file, which is exactly
> why `Listener.transient` treats a `.scope` as per-launch by
> construction. Measured live: **0 of 30** keys end `.scope`. Driven as a
> counterfactual against a real listener in a real
> `systemd-run --user --scope`, admitting the holder to `holders` gives
> **0 findings either way** — the port moves from `if not seen` to
> `if not owner` and nothing else moves.
> **The population refutes it a second time.** Of the **190** stored
> sweeps carrying a ports blob, **129** already carry a transient holder
> on a registry-claimed audited port: 1716 (`_kdeconnectd_`, 107), 3300
> (`venture-assistant`, 22, 2026-08-24 → 08-26) and 8700
> (`InvestingAssistant`, 7). **None is a fault** — 1716's registry cell
> says it is not a project and is tied to the desktop session, and the
> other two say *"dev server for now"*. So the founding specimen is what
> two of the three rows predict in writing, and the family would fire on
> **68 %** of all sweeps.
> **And it inverts the direction**: widening `holders` can only ever
> *remove* a `wrong_project` row, since a port with two holders is
> skipped in favour of `port_shared`. Empty population, measured — 0 of
> 190 sweeps have carried both kinds on one claimed port.
> **The half that would have been built already exists.**
> `PortAttribution.reading()` answers `transient` for this port and
> `as_blob` publishes `transient_ports`, both from Session 128 for a
> neighbouring reason — so the declined judgement is recorded and
> nothing is added. What ships is the record, four falsified tests, and
> `SNAG-PORT-005` for the residue: the real squat's discriminator is the
> holder's **working directory**, and that dies too, because
> `~/projects/web/portfolionew` carries no `.project.yaml` and is not a
> registered project.
> The aside — `unknown_registry_projects == ['sysadmin-service']` — is
> **not a second finding**: it is `SNAG-ESTATE-005`, delegated since
> 2026-08-15 and watched every sitting.

> **The entry counted six stale figures and the tree held four, one of
> them exact** (2026-09-13, Session 222, closing `SNAG-DOCS-012` and
> opening `SNAG-DOCS-026`).
> `README.md` has been public since 2026-09-09 and states seven moving
> figures. Two were hedged, dated and inside their guard's band, so they
> were behaving as designed rather than failing. The handoff's `58,073`
> is not the backend's line count — it is `sysadmin/` at **51,923** plus
> `sysadmin_tray/` at **6,150**, set against a sentence naming the
> backend alone, which reads **1.0 %** adrift. The tray's **6,150** was
> **exact**, and had been called stale by two consecutive sittings that
> had not measured it. A seventh figure nobody had named — the install
> block's *"~3,960 tests"* against **4,087** — moves faster than any of
> the six. **The entry's own lesson arriving at the entry**: a figure
> quoted in prose is free to be re-scoped by whoever quotes it, and the
> quoting sittings were its own.
> **The flapping precedent does not transfer, and that is what decided
> the remedy.** Those figures went because a marker claimed a
> verification that had not happened and because `check-ops-claims.sh`
> prints the live reading to the same reader at every preflight. Neither
> limb holds here: no marker claims these, and this document's reader is
> a stranger on `github.com` who never runs preflight, for whom the
> figure is not a second statement but the only one.
> **So the treatment is the one this document already had, applied to
> the figures it had been scoped past.** `LINE_COUNT_CLAIMS` carries
> five as `(pattern, pathspec)` pairs, each naming its own denominator
> so it cannot be re-scoped the way the prose was; both sentences are
> re-measured, hedged and dated, and the third copy in `docs/README.md`
> with them. The claim they support is asked of the **tree** directly,
> because five figures may each drift within tolerance while the
> comparison between them reverses.
> **The test count defers rather than being measured twice.** Collecting
> inside the suite is this module's own recorded refusal and one real
> `measure_tests()` was timed at **1.9 s**, recursively, for a figure
> this row already states behind its marker. It is compared against that
> checked cell through `ops_claims`' own pattern, so README drifting from
> `STATUS.md` is red in the suite and `STATUS.md` drifting from the box
> is `check_tests` at the next preflight.
> **Seven mutations; one passed against deliberately broken code and is
> filed rather than closed.** Restoring the pre-fix figure under today's
> hedge and date passes at 6.7 % against a 15 % band — the band checks a
> **value** where the date asserts a **provenance**, which no test can
> witness (`SNAG-DOCS-026`). Two more were insufficient before they were
> sufficient: removing one spelling of this row's checked cell changed
> nothing, because the cell states the count twice on purpose and the
> alternation reads both; and the first draft asserted readability in a
> **fixture**, so a removed cell errored every test in the class
> including the premise written to name the cause — Session 130's
> recorded defect, repaired until the premise failed and said *"the
> block states 2 different figures"*.
> **`tracked_lines` was written twice and is now written once**, in
> `tests/document_claims.py` beside `FIGURE_TOLERANCE`, for that
> constant's own stated reason — two implementations of one measurement
> being the defect these guards exist to catch, arriving inside them.
>
> **A marked sentence may state no figure, so four of them were deleted**
> (2026-09-12, Session 221, closing `SNAG-DOCS-025`).
> The two `<!--check:flapping-->` sentences below now carry the
> **judgement** — this title is declared flapping and set aside — and no
> measurement at all. `check_flapping` reads a predicate, never a number,
> so the duty cycle and the episode count beside it were unread; and an
> unread figure beside a marker does not read like unread prose, it reads
> as **verified**, which `check_markers`' own docstring names as worse
> than prose because prose does not claim to have been checked.
> **The entry said correcting them would buy a day and it bought less.**
> `9467176` wrote 4.2 %/26 and 0.8 %/12 on 2026-09-11; Session 220
> measured 3.0 %/22 and 0.6 %/10 the next day, and this sitting measured
> **23** episodes for the VRAM title an hour later — the quantity moving
> between the filing and the fix, which is the argument for deleting
> rather than re-measuring, stated as an observation instead of as a
> prediction.
> **The guard is a test and could not have been a snag check.** A check
> asserting the sentence states no figure asserts the *fix*, and
> `check-snag-claims.sh`'s `ok` means *the bug is still real* — so it
> would report `still holds` over a landed closure for ever, which is
> `check_review_schedule_unread`'s defect. `tests/test_ops_claims.py`'s
> `TestAMarkedSentenceStatesNoFigure` outlives the entry instead
> (`FROZEN_TABLES`' rule).
> **A backtick is the difference between a name and a measurement**, and
> the live block is what forces it: the declared title is
> `High VRAM usage on AMD Radeon RX 7900 XTX`, so a naive digit gate goes
> red on a sentence that is *correct* and the obvious repair to that red
> is to reword the document to suit the guard. The gate blanks code spans
> with `CODE_SPAN_RE` — the module's own spelling, the one `read_markers`
> uses to find these markers — which is `status_figures`' *"Phase 3 is a
> name"* and `health_review`'s refusal to put a service name through a
> digit gate, met a third time. The exemption is held by a **premise**
> test rather than asserted twice, so the day no declared title carries a
> digit the suite says the branch has emptied.
> **Four mutations, and only one of them reddens the drive that matters.**
> Restoring a figure to `STATUS.md` and widening the scope to the whole
> region each redden the property test; dropping the code-span exemption
> reddens it beside the detector drive; and a gate returning **nothing at
> all** — the mutation that makes every other test pass — is caught by
> the drive at the two sentences `9467176` shipped, verbatim. That drive
> is why the class is four tests and not one.
> **The scope is the marked sentences and nothing wider.** The same
> paragraph records `venture-chat unreachable` at **11.3 %** across 9
> episodes as evidence for *not* declaring it, and Session 216's own
> account above states the figures it measured before designing rule 12.
> Both are unmarked, so they read as what they are — prose, and
> `SNAG-ESTATE-012`'s class rather than this one. A gate over the region
> would delete them, which is a judgement nobody has taken; a test pins
> the narrowness so a later widening is a decision.
> **The suite went red with no source change, and the cause was the same
> commit** (`SNAG-TEST-013`, filed and fixed here). The live test one
> class over asserted `count.measured == str(facts.unresolved)`, which
> holds only while no declared flapping title is *genuinely* open;
> `Unusual CPU usage` opened between two green runs an hour apart, the
> checker correctly set aside two rows rather than one, and the assertion
> read `assert '4' == '5'` while `check-ops-claims.sh` reported `ok` on
> every claim in the same minute. `git log -S` puts it in `9467176` — the
> commit that moved the *document* off the flapping value and left a
> *test* pinned to it. At least one of the two titles is open **3.66 %**
> of the window across 33 merged episodes, so it was red about one run in
> twenty-seven and blocking at the close, which is what that class's own
> docstring forbids three paragraphs above the assertion. It is a
> **differential** now — injecting a flapping row must move neither the
> figure nor the verdict — which is box-independent and is what the test
> was always for.
> **One control was a no-op and said so only because it was asserted.**
> The first falsification was written as `python3 -c` with backticks in
> the string, which zsh command-substituted; the mutation never reached
> the file and all four tests passed, which is indistinguishable from a
> guard that works. The rewrite asserts the replacement landed before
> running anything.
>
> **The ranking was empty, so the sweep was the sitting**
> (2026-09-12, Session 220, opening `SNAG-DOCS-025`).
> `owed` is the one disposition that is a work queue, and **zero** of the
> open entries declared it for the second sitting running — so the
> handoff's own stated fallback was the live branch, and all eleven open
> entries that name no check were re-measured against the box and the two
> trees rather than re-read. Eight are unmoved; three moved, and two of
> those three could not have been seen by re-reading.
> **A fix can be quiet and untested at the same time.** `SNAG-GPU-001`'s
> predicate has written **2,239** `service_health` rows since it landed
> on 2026-09-08 and `context_lost` is false on every one — because the
> newest kernel reset is 2026-09-06 20:43:01, against the eleven in seven
> days the entry was filed on. The box also changed kernel on 2026-09-10,
> `7.2.3-arch1-2` to `6.18.49-2-lts`, so the live spelling of the reset
> line moved to the form `CRITICAL_SIGNATURES` declares for LTS. Quiet
> and working are not the same fact, and nothing here separates them.
> **An entry's own lesson landed on the entry.** `SNAG-DOCS-012` names
> four documents as carrying *"lines of roadmap narrative"*; `CLAUDE.md`
> never has, and two of the others carry the *correction* rather than the
> error — while `README.md`, the public surface the entry calls already
> correct, has itself gone stale two days after being written.
> **A claim two entries share was measured with the wrong instrument.**
> Both say *"estate-manager's register mints"* and list ten families;
> driven through the estate's own `estate.snags` reader it mints **one**,
> 185 of 185 being `SNAG-ESTATE`, and the ten are families their document
> *cites*. Both conclusions survive by a wider margin than claimed.
> **What the sweep turned up is filed as the register's only owed
> entry.** Two `<!--check:flapping-->` sentences state a duty cycle and
> an episode count that their marker does not read, and on the day after
> they were written all four figures were wrong. An unmarked stale figure
> reads as prose; a marked one reads as verified, which is worse.
>
> **Having sessions was not sufficient and now there is a reader**
> (2026-09-12, Session 219, closing `SNAG-DOCS-022`).
> `scripts/check-estate-docs.sh` reads `GET :8400/api/audit/findings`
> and prints the `docs` findings whose `detail.project` is this
> repository; `scripts/claude-preflight.sh` §6.7 calls it at every
> session start. It judges nothing and raises nothing —
> `JUDGED_AUDIT_CHECKS` did not move and no clause of its ownership test
> changed, because a reader is not a second owner.
> **Scoping to `docs` is a measurement, not a habit.** Counting
> `Finding(` against the `detail` dicts in all **13** of the estate's
> check modules, `docs` is the only one where every finding carries the
> project key — **7 of 7**, against **0 of 12** for `pointers`, **0 of
> 2** for `wiring`, **2 of 9** for `consumers`, **1 of 6** for
> `readers`. For any other check a project-keyed reader is blind on most
> of the population and cannot say so, which is `ports_checked`'s rule.
> **The spelling is derived and the mutation is why.** The name is this
> checkout's real path relative to the projects root — `entry.relative`,
> what the audit keys on — never a literal. Driven: a reader keyed
> `sysadmin-assistant`, which is what the **register** resolves this
> repository to, exits **0** with **empty output** against the real
> 2026-09-11 finding. Green, silent, and wrong for ever.
> **Blind is not clean, in four shapes**: an errored `docs` check, an
> absent one, a finding naming no project, and any way of not reaching
> `:8400` are all exit **2**. Preflight renders 2 as *could not be
> read*, never as *none* — its own `ports_checked` convention, already
> written into the open-snag section below it.
> **The rung printed is the producer's**, and preflight does not strip
> it, which is where this section departs from the two beside it. The
> first draft did strip it and only rendering the banner said so.
> **Ten mutations were driven** and each reddens the right tests, four
> of them against preflight rather than the reader; the producer pin is
> driven at three modules that must trip it, because `assert not
> missing` is satisfied perfectly by a walker that has stopped looking.
> **An existing guard caught the fix** — `test_live_drive_premises.py`
> reported the new file opening a live connection while marking no
> premise, so the live class carries one: both live witnesses believe a
> **negative** that an audit which never ran satisfies perfectly.
> **Population at the moment of the fix is zero**, which is the
> measurement and not a gap: the 2026-09-11 breach against this tree was
> repaired the same day, so the live audit's two `docs` findings are
> both `ml/Athenaeum`'s and the reader exits 0 in silence.
> Residue `SNAG-DOCS-024` (`pointers` walks every repository and
> publishes no project key, so its findings about this tree still reach
> no sitting — one keyword argument at the producer, and the ordering
> matters: the key exists first or the widening reads zero).
> **A restart was owed and paid once**, `sysadmin/estate/judgements.py`
> being in the daemon's import graph and the edit being the docstring
> sentence that enumerated the carriers, which this fix made false.
> Daemon restarted at 2026-09-12 16:43:49, `NRestarts=5`, `/health` 200
> — *the two markers that stood on this line moved to the 2026-09-13
> entry at the top of the block when Session 227 restarted again; a
> marker names the check and the check reads the box, so it belongs
> beside whichever sentence states the current answer.*
>
> **Having sessions is what everyone assumed was sufficient, and this
> repository is the counter-example**
> (2026-09-12, Session 218, answering estate-manager's message
> `03bcaf7c-816e-42bf-be5a-0c3554c8e399` / their ADR-0163).
> Their measurement: rule 3 of `sysadmin/estate/judgements.py` directs
> other repositories' conformance breaches to *"those repositories' own
> ADR processes"*, and where a repository has **no sessions** that
> direction reaches nobody — `ml/Athenaeum`, a `docs` breach standing
> **17.7 days**, **0** transcripts against a live corpus of 640. Nothing
> was asked.
> **The second half was measured here and is wider.** A `docs` finding
> was filed against **this** repository at 13:55 on 2026-09-11 and
> reached no session either: `scripts/claude-preflight.sh` names `:8400`
> nowhere, `inbox-notice.sh` fetches `/api/estate/messages` and nothing
> else, `session-notice.sh` only publishes outbound, and this module's
> own hourly pull filters on `JUDGED_AUDIT_CHECKS`, which does not name
> `docs`. A sitting found it by going to look. Having sessions is
> necessary and **not sufficient**; what is missing is a *reader*.
> **`docs` is refused for `JUDGED_AUDIT_CHECKS` and the refusal is
> recorded** rather than left as a silence (`SNAG-CFG-001`'s shape, the
> argument the `info` codes already get). Clause 1 of the ownership test
> fails outright — `ml/Athenaeum/HANDOFF.md` belongs squarely to
> `ml/Athenaeum`, where a port belongs to no repository — and the
> population would be every repository on the box. A single surviving
> clause is a reason to fix the **carrier**, not to move the judgement.
> Note the direction: `docs` emits `breach`, so a rung-only filter would
> have taken it silently.
> **The guard that shipped is not their check relocated, and the
> operands say so.** Theirs compares the next action against the
> handoff's own date; `tests/test_handoff_shape.py` rule 3 compares it
> against the `## Scheduled action` section **beside it** — one document
> read against itself, which is ADR-0008's line between two checks.
> **The naive rule was measured and refused.** Over all **248**
> published next actions in this file's history, *"names any date later
> than the handoff's own"* fires **7** and **2 of the 7 are correct
> lines** — `91fd90e7`'s date is a deadline, `305152a4`'s is the subject
> of the work — which is why the producer files at `warn`. A blocking
> guard refusing 2 in 7 well-written lines teaches the operator to reach
> for `--no-verify`, `SNAG-DB-005` rule 3. The rule that ships fires
> **2 of 248** with **zero** false positives.
> **No wall clock is read**, deliberately: both dates come from the
> document, so the verdict is a property of the file and cannot move
> between two runs of one commit.
> Residues `SNAG-DOCS-022` (the carrier) and `SNAG-DOCS-023` (the rule
> is blind to a gate the section never declared — 1 live miss in 248,
> and closing it needs prose parsing `SNAG-ESTATE-012` refuses).
> **A restart was owed anyway, and the reason is worth the line.** The
> edit is docstrings only and changes no behaviour, but
> `sysadmin/estate/judgements.py` is in the daemon's import graph and
> `check_deploy` compares **mtimes**, which cannot see the difference —
> so it reported `no` correctly. Paid rather than argued around: a
> standing `no` is one the next sitting has to re-derive, and this is
> not `SNAG-SYSD-009`'s over-report, which is about modules the daemon
> cannot reach. Daemon restarted at
> 2026-09-12 at **16:07:06**,
> `NRestarts=4`, `/health` 200.
> **It was paid three times, and the ordering is the transferable
> part.** Each restart was taken while a further docstring edit was
> still to come — one of them a rewrap of the very paragraph recording
> the first — so `check_deploy` went stale again within minutes. The
> mtime comparison is against the **newest source edit**, not against
> the commit and not against behaviour, so every source edit must land
> before the restart rather than around it, and a docstring costs
> exactly what a branch does. Four starts against `StartLimitBurst=5`
> in 600 s, which is the budget `SNAG-SYSD-007` is about: one more and
> the limiter would have made the loop terminal, which is the 77-minute
> outage that entry was opened by.

> **A flapping title cannot be pinned by a count, so the pin became the
> stable set and the flap is declared beside it**
> (2026-09-11, Session 216, closing `SNAG-DOCS-015`).
> The block's unresolved-alert figure was pinned over *every* open row,
> which is right for a fault that opens once and stays open and has no
> satisfiable value for one that opens twenty-six times a week: the same
> checker read **4, then 5, then 6, then 4** across the minutes of one
> close. `ops_claims` rule 12 pins the **stable** set instead — a title
> the block declares is *set aside* by `check_alerts` and judged by
> `check_flapping`, the third reading `ports_checked`'s rule kept asking
> for, so the row is neither counted against the pin nor silently dropped
> from it.
> **Both duty cycles were re-measured before anything was designed, and
> both survived the roll**: `High VRAM usage on AMD Radeon RX 7900 XTX`
> **26 episodes at 4.2 %** of seven days (was 24 at 4.8 %) and
> `Unusual CPU usage` **12 at 0.8 %** (was 11 at 0.7 %).
> **A third specimen the entry never saw is measured and deliberately not
> declared.** `venture-chat unreachable` reads 9 episodes at **11.3 %** —
> an order of magnitude above the CPU title — but its mean episode is
> **2.1 hours**, which is an outage rather than a flap, and no sitting has
> been made to re-pin by it. A declaration is a judgement this document
> makes and the check only bounds; declaring everything the duty cycle
> admits would empty the pin of meaning.
> **The threshold is derived and has nothing in it to tune.** A pin names
> the state a row is in for *most* of the window, so **half** is the point
> at which the honest pin changes side rather than a tolerance somebody
> chose — the entry's own *"4 is the honest pin and 5 is wrong 95 % of the
> time"*, stated once.
> **The window has a control the entry did not have, and it is what sizes
> it.** `High disk usage on /` has been open continuously since 08-30 and
> is a pinned member: it reads **100 %** of a 7-day window, 84 % of a
> 14-day one and **39 %** of a 30-day one, so a month-wide window would
> admit this box's most durable standing fault as a flap. Deliberately not
> `reliability.window_days`, whose own argument is a `service_health`
> retention cap that does not transfer — `alerts` keeps 180 days.
> **The two closures the entry refused in writing are refused by
> construction.** Nothing reads `notifications.tray.flap_cooldown_seconds`
> or anything else the tray owns, and nothing pins a *range* — the claim
> is still one number over the stable set, so a stable row resolving still
> moves it and `SNAG-ESTATE-008`'s **fall** is reported unchanged, driven
> rather than asserted.
> **The quiet verdict is affordable for a structural reason**: an open row
> has an episode inside the window by construction, so a declaration with
> no reading is one setting nothing aside — the diagnosis is `unknown` and
> the consequence is `check_alerts` at exit 1.
> Ten mutations, each red on the intended test; the one expectation that
> was wrong was wrong in the safe direction, a quoted marker being
> stripped a layer below where this fix was looking. `SNAG-DOCS-021` is
> the residue. `sysadmin/ops_claims.py` is outside the daemon's import
> graph, so **no restart is owed**; suite **4018 → 4042**.

> **The rule required a pointer and the entry read it as a link**
> (2026-09-11, Session 215, closing `SNAG-DOCS-020`).
> `tests/test_doc_links.py` asserted a link exists **on disk**, and this
> box holds the private sibling trees a public reader 404s on — so **17**
> links reaching out of this repository with `../../../` passed every run
> since the guard was written. A guard green because it is looking at the
> wrong filesystem is `ports_checked`'s rule at the size of a link.
> **The entry's second measured reason was refuted, not implemented.** It
> prices the fix above a one-liner because four pointer stubs are
> *required to escape* by *a moved document leaves a pointer, never a
> copy*, and so need an exemption declared in a document. The rule
> requires a **pointer**; a pointer is content and a link is mechanism.
> estate-manager's `estate-rules.md` states the rule and says nothing of
> form; **their own copies of those same four moved guides** cite back at
> this tree as a plain backticked path, not a link; and this tree already
> spells the same citation unlinked **112** times against **12** linked.
> So all 17 became plain citations and there is **no exemption list** —
> the population is empty *by repair*, leaving no switch.
> **The entry's partition was short by one document and two links.**
> `docs/adr/0002-estate-manager.md` is a fifth pointer stub carrying
> **two** escapes, one of them citing the estate's `docs/adr/README.md`,
> which the pointer rule does not require — so the exemption as designed
> would have excused a link nothing obliged. The split is 6 stub links
> across 5 stubs and 11 in arguments, not 4 and 13; the headline 17 is
> confirmed exactly.
> **The obvious one-liner has a wrong version that passes all 17.**
> `Path.is_relative_to` is lexical and does not collapse `..`, so
> `<repo>/docs/adr/../../../estate-manager/x` reads as *inside* —
> measured `True` for every one of the 17. Resolve-then-compare is driven
> at the refuted form rather than left to a comment.
> **One of five falsifications passed against deliberately broken code**:
> once every escape is repaired no link is both outside *and* absent, so
> `missing_links`' containment clause is unreachable — `chk_run_status`'
> redundant-conjunct rule, and a population was built for it.
> The sibling half owes nothing and stays untouched: a commit message is
> not a tracked document, and `estate-manager ADR-0155` degrades to a
> *pointer* where a bare register id degrades to zero. No `sysadmin/`
> module changed, so **no restart is owed**; suite **4013 → 4018**.

> **Two readings of one corpus inverted the number the decision was to
> rest on** (2026-09-11, Session 214, closing `SNAG-DOCS-016` with
> [ADR-0011](../adr/0011-a-cited-register-id-is-a-claim-about-this-repository.md)).
> The entry had **decided against deciding** and was right to: it was
> declining against a pending input, estate-manager having ruled its own
> citation form binding *its own sessions only* and recorded the
> estate-wide form as a recommendation for the owner. The owner ruled on
> 2026-09-10 — each repository decides for itself, the estate publishes
> the **method** rather than the answer — so the refusal expired rather
> than being overruled, which is the thing this close had to say first.
> **The handoff nominated the direction split as decisive and it cannot
> be.** estate-manager read 17 of 31 own filings glossed against 22 of 43
> received — no separation; this sitting read the same predicate over the
> same corpus and got **12 of 31 against 27 of 47**, the own half markedly
> worse. Aggregate gloss agrees almost exactly (**39** either way), so the
> reading carries the case that something is owed and is not asked to
> decide the form.
> **What decides it is compulsion, which is not a reading.** The
> announce-by-filing rule *requires* the id for the 31 sites citing a
> filing this sitting made and requires nothing at all for the 47 citing
> one it received — so an own filing's id is the only witness to a claim
> this repository makes about its own compliance and is written **whole**,
> and a received id is volunteered provenance for a claim the change
> already witnesses and stays **short**.
> **Their figures reproduce, and the one disagreement is definitional.**
> At their boundary: 47 citing commits, 43 received sites, 0 whole — all
> exactly theirs. Their 74/31/1 reads here as 73/30/**0**, the whole
> difference being `ebd58df` citing one id in *both* forms and counted
> once here and twice there. So *1 of 31 by whole uuid* was a body line
> restating the subject's short id, not a sitting choosing the wide form.
> **Disclosure is not a term, for a reason stronger than the one offered.**
> The register is a live service and **no tree holds its rows** — 136
> messages in `cross_repo_messages`, estate-manager's tree holding only
> ADRs and drivers *about* it — so resolvability turns on `:8400` and
> retention, never on who can read the tree. All **57** distinct ids cited
> here still resolve today.
> **Four structural hypotheses, all four refuted**, which is what leaves
> the rule binding the sitting rather than a template: the house `Filed at
> … as <id>` clause (52.6 % against 47.5 %), an id trailing a subject line
> (50.0 % over 8), a commit citing several ids (52.9 / 31.2 / 57.1 %, not
> monotone) and an id sharing its sentence (**50.0 % against 50.0 %**).
> The first was written down as a finding before it was measured.
> No code changed, so **no restart is owed**; the suite is unmoved at
> 4013 and `docs/adr/` goes ten records to eleven. `SNAG-DOCS-020` is the
> residue — 29 commits citing a foreign ADR and 17 tracked-document links
> resolving on this box and nowhere else, which `tests/test_doc_links.py`
> passes because it checks existence on disk.

> **The convention had been honoured 162 times and written down nowhere**
> (2026-09-10, Session 213, closing `SNAG-DOCS-019`). `read_claim`
> refuses a region stating one claim two ways, and the region is the
> *narrative*, which is append-only — so every claim in this block puts a
> standing obligation on the sitting that rewrites it: **the sentence it
> supersedes must stop matching the pattern.** Session 212 met that
> obligation by breaching it, and nothing anywhere said what the remedy
> was. `tests/test_ops_claims.py::TestSupersededClaimsAreDemoted` states
> it now.
> **The guard is written over every pattern-bearing claim**, not over
> `daemon_start`. The obligation is rule 2's and belongs to all seven
> keys; `daemon_start` is merely where it bites, and `tests` is the
> second live member — it states its figure twice on purpose, once in the
> Status cell and once in the Notes, so the day those part company it
> fails here for the same reason. That row is also what forces the
> spelling: it matches **twice** and states **one** figure, so a guard
> written on match count would be red on a healthy document.
> **The entry's measurement was right in direction and short by two
> axes.** It counted six historical restarts spelled time-only; the live
> region carries **ten** superseded records in **four** spellings — 5
> unbolded and time-only, 3 unbolded with the date, 1 bolded with the
> `at` dropped, 1 with the date moved out of the bold, which is Session
> 212's own repair. They share only the property that matters, so what is
> pinned is *the claim reads one value* and never a spelling: pinning a
> spelling would turn the guard red on a demotion that works.
> **162 of 262.** Every revision of this file replayed through
> `printed_region`: of the 262 commits whose region parses, **162** hold
> exactly one full-datetime restart claim, **100** hold none, and **none
> has ever held two**. Session 212's collision lived in the working tree
> and was repaired before the commit, which is why no revision records
> it.
> **The vacuity risk ran the other way, and that is why there are two
> witnesses.** `at most one` is satisfied by *none*, so a reworded
> sentence or a broken pattern would leave the guard green while the
> claim had gone blind — `ports_checked`'s rule at the size of an assert.
> The assertion is therefore *the reader returns a value*, and both
> witnesses splice a **synthetic** sentence onto the live region, because
> a witness built from today's wording goes vacuous on the edit that
> moves it.
> **Five mutations driven, and one settles whether this is a second copy
> of `check-ops-claims.sh`.** Taking the newest match instead of refusing
> — the narrowing the entry rejected in writing — reddens
> `test_an_undemoted_predecessor_is_what_the_guard_refuses` alone; driven
> under that narrowing **beside a real undemoted collision written into
> this file**, the checker reports `ok Daemon start time` and exits 0. A
> check cannot detect a change to its own resolution rule. Widening the
> pattern to read the demotion too reddens three here and
> `test_the_demotion_is_the_repair_and_the_claim_reads_again` **alone**
> at a document whose demotion uses one of the other three spellings —
> which is why that test is synthetic end to end.
> **The sitting never met the convention it pinned**, the entry's own
> invisibility arriving inside its fix: `ops_claims.py` is outside the
> daemon's import graph, so no restart was owed, no restart sentence was
> written, and nothing needed demoting. The other two candidates the
> entry named are **declined rather than deferred**; what went beside the
> pattern is a *pointer* to the test, since a comment and a test both
> stating a convention are two statements free to disagree about it.
> Suite **4009 → 4013**.

> **The wrapper was the contract, and the payload could not witness its
> own deploy** (2026-09-10, Session 212, closing `SNAG-DOCS-018`).
> `GET /api/services/by-project` is the one surface this repository
> *publishes* to another repository, and it declared `response_model=dict`
> from the day it shipped — which pins nothing, while the two `:8400`
> seams this repository *consumes* are both modelled here against the
> estate's `response_model=`. The seam running outward was the only one
> with no shape written down at either end. It is
> `ServicesByProjectResponse` now, one field over `dict[str, list[str]]`.
> **The routing correction is the transferable half.** `SNAG-DOCS-017`
> sent this question to the estate under *a question routed to the owner
> is answered by the owner*; that rule states its own test — would
> answering it differently change what another repository must do? — and
> a `response_model` changes no byte and asks nothing of them, so the
> test sends it back. Reading the rule by its **name** rather than by its
> **test** is what mis-routed it.
> **The wrapper is pinned, never the mapping, and that is the whole
> design.** estate-manager reads `payload.get("by_project", payload)` —
> two limbs, the second accepting a bare mapping — so pinning the bare
> mapping was the smaller-looking model and would have **changed the
> wire under them**. Pinning the wrapper makes their second limb
> *unreachable* rather than merely unexercised, which is the difference
> the Contract Registry is about: a producer's guarantee is not the same
> object as a consumer's defensiveness. Their parse is deliberately not
> imported or reproduced here — modelling a consumer's tolerance in the
> producer's suite is that collapse arriving as a test.
> **Byte-identity was measured twice rather than asserted.** The live
> payload captured before the change and the pinned app's response after
> it are identical at **603 bytes**, same content-type; captured again
> across the restart it is identical a second time. Which is exactly why
> **the payload cannot witness its own deploy** — a discriminating
> witness was needed and `/openapi.json` is it: the route now answers
> `$ref: ServicesByProjectResponse` where it answered a bare object.
> The unasked-for dividend is that the shape is **discoverable** at the
> producer for the first time; until today the only statement of it
> anywhere was the consumer's coercion.
> **No `count`, refused on measurement rather than on taste.** Every
> sibling in `contracts.py` carries one because an empty list is
> ambiguous between *nothing to report* and *nobody looked*;
> `get_services()` **raises** on a `services.yaml` it cannot read, so the
> failure is a 500 and the mapping is never empty-because-blind. The
> ambiguity those counts resolve does not arise here, and the field would
> have changed a payload announced as changing none.
> **The route had no test of any kind**, which is `SNAG-API-004`'s
> `/api/projects/managed` one seam over — the surface another repository
> depends on was the unexercised one. Eight now.
> **Six mutations driven, every one red on its intended test, and one of
> them was the entry's own claim about a test.** `SNAG-DOCS-018` asserted
> that no new guard was owed because the membership sweep refuses an
> exemption to a pinned route; that is a claim, so it was driven —
> restoring the exemption row beside the landed pin turns
> `test_no_pinned_route_appears_in_the_exemption_table` red, and deleting
> the registry row turns `test_every_pinned_route_has_a_registry_row`
> red. The document cannot fall behind the code here, measured rather
> than believed. Registry membership goes **30 → 31** pinned of 51 live
> pairs, the exemption table **twelve → eleven**, and the second limb of
> `live_route_contracts`' `None` — *declares a model that is not a
> contract* — empties, this route having been its only member.
> Suite **4001 → 4009**. Announced at estate-manager before the commit
> that carries it, message `fc6f769f-31a8-427a-b772-e4a0172b8d32`, cited
> whole because a short id resolves on no route (`SNAG-DOCS-016`).
> Daemon restarted at that session's close
> — owed, because the changed router is in the daemon's import graph,
> and paid once. *(The instant was written here and is dropped: the
> `daemon_start` claim is a single live figure, and a second timestamp
> anywhere in the parsed region makes it `unknown` under rule 2 — a
> block stating one figure two ways. git holds the history.)*

> **A name in the tray is not a parse, and the refused implementation
> ships green** (2026-09-10, Session 211, closing `SNAG-DOCS-017`).
> Session 210 settled registry membership as *a `contracts.py` model is
> bound to the route* and computed only the **producer** half of it,
> which FastAPI stores on the route object. The other binding is held
> nowhere: the pairing between the URL requested and the class the reply
> is handed to exists only as **adjacency in a function body**, so
> `document_claims.tray_consumption` walks `sysadmin_tray/` for it.
> **8 routes belong in this table by the consumer half alone** — the
> tray parses 16 pairs with a contract, 14 served here and 2 the
> estate's, and 6 of the 14 are `response_model`-pinned as well, so
> their membership never rested on prose. The eleven parse-side claims
> come back **10 confirmed and the eleventh honest**; the entry counted
> nine, which is the served table alone.
> **The refused implementation was driven rather than argued.**
> Detecting the indirect fetch helper by **name** gives the identical
> answer today — one helper, sixteen parses — so the structural version
> looks like ceremony. Driven at a *second* helper added under a
> different name and parsing an exempted route, the name-keyed walk
> ships **entirely green** while the structural one goes red on three
> tests: the silence this entry is about, reproduced inside the fix for
> it. That is why the discrimination is a test and not a docstring
> claim.
> **Three obstacles the entry did not name, each producing a smaller and
> entirely plausible answer.** `fetch_status` requests **twice** —
> `/health` for liveness, then `/api/sysadmin/status` — so pairing at
> the function reports the tray parsing `/health` with `StatusResponse`;
> the anchor is the nearest preceding request, and this tray's one
> two-request method is the whole population of the rule. Two pairs are
> the estate's, so `_estate_api_url` renders the `:8400` prefix the
> consumed table already writes, or the walk reports this service as
> serving them. And `_fetch_file_endpoint`'s path is a **parameter**, so
> the predicate that reads a direct call correctly refuses it and one
> predicate silently drops 5 of the 16.
> **It closes the half rule 1 was missing.** That rule refuses an
> exemption to a route the *producer* pinned; the same clause was owed
> on the consumer side and was unreachable without the walk. The four
> *no consumer* reasons are checkable in **one limb** and the guard's
> name says so — Alfred and estate-manager are outside this checkout, so
> it can refute the claim and never confirm it. `POST /api/files/scan`
> is the one reason confirmed in both directions.
> **One of the sitting's own falsifications was not a mutation at all**:
> the rule 3 drive was staged as a no-op that appended an unused
> function, and recorded as a passing control. A control that changes no
> behaviour tests nothing and reads exactly like one that does. Replaced
> with the real narrowing; **16 mutations** driven, 14 red on the
> intended test and two labelled controls green. Suite **3988 → 4001**;
> nothing under `sysadmin/` changed, so no other entry's instrument
> could move and no restart is owed. Filed `SNAG-DOCS-018` (P4): the one
> seam this repository *produces* for another is uncontracted at **both**
> ends, and the estate's own routing test sends that question back here.

> **The entry priced a judgement and the binding was readable**
> (2026-09-10, Session 210, closing `SNAG-DOCS-014`). `CLAUDE.md`'s
> Contract Registry closes by stating that *"membership is a property a
> test computes"*; the test it means walks field annotations from every
> root, which is a property of the **models**, so a route added with no
> row was invisible to the mechanism the document named as its
> guarantee. The entry asked for *a decision about which of the twelve
> the registry is meant to hold* and priced it per route — an SSE
> stream, a `410` tombstone, a manifest another contract describes.
> Measuring the **binding** rather than reasoning about the payload
> settles all twelve at once: **a route belongs in the registry iff a
> `contracts.py` model is bound to it**, and the producer half of that
> is `response_model=` naming a class in that module.
> **That rule found two live defects the entry had grouped with the
> absences.** `GET /api/logs/review` and `POST /api/logs/review/generate`
> both carry `response_model=LogReviewResponse` and had no row, while
> the document's prose discusses the log review at length as one of its
> four Tier 3 reviews. Of **51** live `(method, path)` pairs, **30** are
> pinned and **28** had rows; the remaining **21** are unpinned, **9**
> held as parse- or serialise-side rows and **12** now declared in the
> document with a reason each.
> **The exemption table cannot hide a contract, which is what stops it
> being a switch.** A pinned route is *refused* an entry there, so the
> list can only ever excuse what the code has already left unpinned —
> `check_markers` rule 1 met from the other side. And it is declared in
> `CLAUDE.md` rather than in the test: a list living in the guard
> protects the guard's knowledge and leaves the reader exactly as
> misled, which is the whole of `SNAG-DOCS-001`.
> **Three "stale rows" were the instrument rather than the document.**
> The registry writes `{id}` and `{name}` where the handlers write
> `{alert_id}` and `{service_name}`, so a raw set comparison reports
> three phantom gaps beside three phantom stale rows. `normalise_path`
> collapses the spelling and its **injectivity over the live set (51 of
> 51)** is a test, because a collapsing instrument compares fewer things
> than it believes; respelling a parameter is the labelled negative
> control and stays green. The rows' **content** was measured before the
> sweep was written and was correct **36 of 36**, so that half ships as
> a regression guard with an empty finding population and says so.
> **One of sixteen falsifications passed against deliberately broken
> code.** The membership-sentence guard read the 200 characters after
> the claim and looked for `models`; the paragraph continues *"It
> carried eight project response models…"* twelve lines down, so it
> matched a different sentence and reported health over a deleted
> correction. An append-only narrative makes a substring test monotonic.
> It is bound to the qualifying sentence's own clause now. The two
> decisive mutations are code-side — a route added pinned, and a route
> added unpinned — because the defect is a route with no row rather than
> a row edited. Suite **3964 → 3988**; the snag controls stash-diffed
> either side came back identical. Filed `SNAG-DOCS-017` (P4): the
> consumer half of the rule is an assertion nine rows make in prose,
> measured true **8 of 8** today and computed by nothing. No restart:
> nothing the daemon imports changed.

> **The entry said there was nothing to repair, and the guard found
> three defects on its first run** (2026-09-10, Session 209, closing
> `SNAG-DOCS-013`). `SNAG-DOCS-011`'s fix swept `docs/ARCHITECTURE.md`
> and left `README.md` and `docs/README.md` making the same class of
> claim unguarded — the worse exposure of the two being the one
> `github.com` renders on arrival. The entry priced the work as *a
> mechanism rather than a repair* because the five agent rows were
> correct; the documents were not. `README.md` claimed **19 migrations**
> against **18** in Alembic's own revision graph, and `docs/README.md`
> did not account for `projects-registry-legacy.yaml`, a file sitting
> beside it in the directory it exists to index. A correctness claim
> scoped to the rows somebody checked is the entry's own lesson —
> instance against class — one level down.
> **The route table stated one fact in two units and neither half looked
> wrong.** The headline counted route *objects* and the rows counted
> distinct *paths*, so they differed by exactly one: `/api/sysadmin/dnd`
> is one path registered by a `@router.get` and a `@router.post`. The
> rows summed to **50** beneath a headline of **51** and no reader could
> reconcile them. The headline was the correct half — this file's own
> `routes` claim reads 51 and checks `ok` — so the row moved to 18 and
> the unit is now stated in the sentence above the table.
> **The intervals derive from the job plan, not from a config leaf, and
> the config-leaf mutation is what proves the design.** The entry asked
> that each document derive its interval from *its `config.yaml` leaf*;
> `plan_jobs` is the one statement of what the scheduler is asked to do
> and one of its intervals is a **derivation** rather than a leaf, so a
> leaf read would be a second implementation of the plan. Moving
> `health_check_interval_seconds` 300 → 600 turns **all three** stated
> intervals red at once, while the diagram-against-table test stays
> **green** — both documents being wrong together is precisely what a
> document-against-document check cannot see.
> **Two of the sitting's own guards were wrong before they were right,
> both times about the document rather than the box.** Reading only link
> targets called five of seven subtrees unnamed, which would have
> demanded the index be rewritten to satisfy the guard's reading of it;
> and counting `.gitkeep` as content made *empty placeholders*
> unsatisfiable in both directions, since git cannot hold an empty
> directory without one.
> **The falsification pass found a false-positive surface nothing was
> aimed at.** The harness writes `*.bak` beside each file it breaks and
> the file sweep walked the working tree, so four mutations about
> `ARCHITECTURE.md`'s schedule went red on `docs/README.md`'s sweep. An
> editor's `.orig` or a merge `.rej` would do the same for no
> documentation fault, so the population is `git ls-files` now — the
> stated cost being that an unstaged document is outside the sweep,
> which is the correct side.
> Nineteen mutations driven, eighteen red on the intended guard and one
> green as designed. The box side is stated once in
> `tests/document_claims.py`. Suite **3915 → 3964** (+5 / +24 / +20,
> which reconciles). **The alerts claim was re-pinned twice in one
> sitting and 4 is the stable figure**: `High VRAM usage` flaps — 24
> episodes in seven days, mean 1029 s open, unresolved for **4.8 %** of
> the window — so a count claim naming it is wrong 95 % of the time,
> which is a shape `check_alerts` does not have a reading for. Filed
> `SNAG-DOCS-015` (P4). Filed `SNAG-DOCS-014` (P4): `CLAUDE.md` is the
> *fourth* document making this claim, and the test its own registry
> cites walks models rather than routes — **12** served paths sit
> outside its table. No restart: nothing the daemon imports changed.

> **The entry counted lines naming a departed component, and a line
> count cannot measure an omission** (2026-09-10, Session 208, closing
> `SNAG-DOCS-011`). `docs/ARCHITECTURE.md` showed `ProjectOrganiserAgent`
> and the `projects/` and `registry/` packages, all gone under
> [ADR-0005](../adr/0005-project-state-leaves.md) since 2026-08-13, and
> the entry measured the defect at **5 lines of 277**. Grep finds **9**
> — and the file's worse fault was what it never named: `estate/` and
> `EstateJudgeAgent`, which are precisely the half that ADR *gave* this
> repository. Corrected the diagram, the package tree, the agent table,
> the router table, the database section and the tray's tabs; a reader
> now finds the judging swap in both directions rather than one.
> **The handoff named the database and the tray as accurate and both
> were wrong on membership.** Measured against the box: the database
> section named **nine**, two of them (`project_snapshots`,
> `log_summaries`) dropped by migration 014 on 2026-08-24, and it omitted
> six that exist — the live schema's count is the one pinned in the Quick
> Status table below, and the section now derives from it. The tray's tab list
> named four of five, missing `Files`. The `projects` router row
> described seven route families where `GET /openapi.json` serves
> **one**, `/api/summary` was credited with project scores its own
> producer docstring says it does not carry, and the test count read
> *~360* against **3900**. A scope claim is a claim, and this one was
> wrong in both directions.
> **The guard is a test rather than a twenty-first snag check, and the
> polarity is the whole argument.** `check-snag-claims.sh`'s `ok` means
> *the defect is still real*, so a check keyed on "does the file name a
> departed component" reports `still holds` over a landed correction for
> ever — `check_review_schedule_unread`'s defect, which this entry
> anticipated in writing. A pytest assertion has the opposite sign:
> green means the file agrees with the box. `tests/test_architecture_doc.py`
> sweeps packages, agents and mapped tables **both ways** against the
> document's fenced blocks — never its prose, because the file must be
> able to record a departure without that sentence tripping the phantom
> sweep. Eight mutations driven, each red on the intended guard, four of
> them modelling an omission. Suite **3900 → 3915**.
> **The diagram is generated and verified rather than hand-aligned.** It
> is built from box columns and widths and the build asserts the tee-offs
> sit above the arrows and the arrows inside their boxes, so alignment is
> a property rather than something that survives until the next edit.
> It also gained the two peers it never drew — estate-manager on
> **:8400** and llama-server on **:8081** — and lost PersonalAssistant,
> which it drew as a live edge while the prose two sections down said the
> integration makes no HTTP call. A dormant integration is prose, not an
> edge.
> **`docs/README.md`'s caveat was retired, because the fix made it
> false.** That section existed to warn a stranger off a stale diagram;
> left standing it would advertise a staleness that no longer exists.
> What replaces it is narrower and about *kind* rather than currency: the
> file describes the system's shape, and the reasoning is `CLAUDE.md`'s.
> **A close note was spent on the wrong message.** `b93fb93c`,
> estate-manager's ADR-0151 ruling, arrived at 07:37 — after the
> once-per-session inbox notice was written — and this sitting closed
> it at 07:48 with a note belonging to `1b37406a`, by resolving the
> notice's short id from `messages[0]` rather than by prefix. There is
> no reopen; the correction is refiled as `8f649e9e` and the right
> message closed with the right note. ADR-0151 is accepted and its
> `reason`-field measurement reproduces here, with a third category it
> does not name — `searxng-upstream` carries a compelled `reason` and
> no `project`, so *"the writing repository"* has no referent there.
> The alerts claim was also re-pinned from **5** to **4** — the fall its
> own note predicted, `Unusual RAM usage` resolving by id. All twelve
> ops claims read `ok`. No restart: nothing the daemon imports changed.

> **The README addressed a reader who already knew this box, and the
> figure it was handed to publish named the wrong population**
> (2026-09-10, Session 207). Publication changed the audience on
> 2026-09-09 and every entry document still addressed the old one.
> `README.md` now opens with the problem before the components — a
> single-user workstation where a unit nobody wired, a migration never
> applied and a fault deduplicated into silence all look like health —
> and frames the roadmap as the artefact
> [ADR-0010](../adr/0010-publication-was-one-option-wearing-three.md)
> published rather than as clutter beside the code.
> **It was also stale in four places, and those are accuracy rather than
> disclosure**, so ADR-0009 and ADR-0010 do not cover them: it listed
> `ProjectOrganiserAgent` and a `sysadmin-organiser` unit, both gone
> under ADR-0005 since 2026-08-13; it described `/api/projects/*` as
> four route families where this service serves **one**; it omitted
> `/api/units/*` and `/api/services/*` entirely; and it listed
> `projects.yaml`, a file that does not exist. The five agents are now
> the five that run, with their intervals.
> **`docs/` had no entry point at all**, so `docs/README.md` is new —
> an index that says which subtree answers which question, and states
> plainly that four of the five files in `guides/` are pointers into a
> repository that is **not public** and will not resolve for an outside
> reader.
> **The handoff's own figure was refuted before it was published.**
> *38,774 lines of roadmap narrative* is every tracked `*.md` file at
> `b900ae3`, reconstructed as an exact match; the roadmap at that commit
> is **24,629**, so the phrase overstates what it names by **14,145**
> lines. ADR-0009 states it correctly in its table and loosely in §3.4,
> and it is the loose form that propagated here, to `tasks.md`,
> `CLAUDE.md` and the handoff. The public README states the population
> instead. Filed `SNAG-DOCS-012` (P4).
> **`ARCHITECTURE.md` carries the same staleness and is filed rather
> than fixed** — `SNAG-DOCS-011` (P3), owed: its diagram still shows a
> departed agent and two departed packages, and `docs/README.md` names
> that in the row that links it. **`SNAG-DOCS` was re-measured and the
> memory index was wrong**: estate-manager mints no numbered
> `SNAG-DOCS-*`; the collision the index reports is their ADR-0051
> *citing* our entry, which is what the rule asks for. Suite **3900**,
> unmoved — a documentation sitting. No restart: nothing the daemon
> imports changed.

> **The deferred publication question had one live option, and the other
> two were removed by re-reading evidence that was already written down**
> (2026-09-09, Session 206, recorded as
> [ADR-0010](../adr/0010-publication-was-one-option-wearing-three.md)).
> **This repository is public**, verified unauthenticated — no token,
> HTTP 200 — which is the honest test, since an authenticated read
> succeeds either way.
> **The handoff offered three options and two were unavailable.** *Ask
> their owners* is **empty**: all 26 private project names resolve to the
> owner's own accounts, so ADR-0009's clause about third parties was a
> **scope** claim and false. *Redact* is unreachable by ADR-0009's own
> argument that publication exposes every commit — the names entered
> history on 2026-08-04, so redaction is the history rewrite that ADR
> refused over **116** cited commit SHAs, and only **2 of 26** were ever
> reachable by a working-tree edit at all.
> **The ruling already made had largely decided the open item.** Nineteen
> of the 26 names sit inside the roadmap narrative the owner had ruled
> publishes as-is; publishing it and redacting its subjects are not
> compatible instructions, and the overlap between two list items in one
> document had never been measured.
> **The audit was re-run at N+1 and moved once.** ADR-0009 measured 347
> commits and its own commit is the 348th, so the last thing to land
> before an irreversible action was unaudited. Everything held except one
> cell: *the owner's real name in no file content* is now **one**
> occurrence, and it is ADR-0009 quoting the address in order to record
> that commit metadata carries it — the commit stating the finding is
> what falsified it. Exposure is identical either way.
> **The sweep nobody had run is third-party personal data**, demanded by
> two school-sounding project names and clean across all 348 commits: no
> pupil, student or client name field, no `.sch.uk` or `.ac.uk` address,
> no date of birth or postcode, and the only human email address in any
> blob is the owner's own.
> **Announced at its measured readers, not at the estate** — alfred and
> estate-manager, because `aad8236` and `d514b39` are the only cross-repo
> writes into this tree, and a `services.yaml` **comment** authored by
> another repository is now published.
> **The scheduled reading was also discharged, two days overdue, and its
> prediction was refuted usefully.** It expected `llm_used` true on all
> three review tables; `health_reviews` is **false**. The lease is not
> the culprit — lease 54 granted at 05:00:05 and released at 05:00:10,
> so `SNAG-SCHED-003`'s fix works — and what failed inside the held
> lease is the inference call, *"Server disconnected without sending a
> response"*. That is the **second limb of a disjunction that entry
> named and never had a specimen of**, every earlier observation having
> been contention. Filed `SNAG-SCHED-004` (P3), discriminator scheduled
> **2026-09-14**. No restart: nothing the daemon imports changed.

> **A remote is two questions with two deadlines, so the urgent one
> stopped waiting on the unhurried one** (2026-09-09, Session 205,
> closing estate message `6e2e5a50` from alfred and this repository's own
> board `top_action`, and recorded as
> [ADR-0009](../adr/0009-the-remote-is-two-questions.md)). `git remote`
> returned nothing, so `services.yaml` — the monitoring configuration for
> all **32** declared services — existed on one disk.
> `git@github.com:DarrenMcG1/sysadmin_assistant.git` is the answer,
> **private**, pushed today: local and remote both hold **347** commits,
> and `git branch -r --contains aad8236` names `origin/main`, which is
> the specific claim alfred filed.
> **The split is the finding, not the remote.** *Where does the second
> copy live* had a live cost and *should this be published* has no
> deadline at all, so bundling them makes a backup wait on a curation
> decision nothing is pressing — and the two differ in reversibility as
> well as urgency: a remote is added and removed freely, while a public
> repository is indexed and unpublishing does not unindex.
> **The publication audit was done anyway and is clean**, measured over
> all 347 commits rather than the working tree, because a key deleted in
> commit 40 is still served at its blob SHA: **zero** key-shaped strings
> in any blob, `auth_token` has held `""` and nothing else for the life
> of the file, no `.env`/`*.pem`/`*.key` ever existed, and the owner's
> real name appears in **no** file content. **It is boring because the
> repository was built for it** — `api.auth_token` ships empty *with a
> startup warning* precisely because `config.yaml` is committed, and
> `ADR-0003` refused three easier homes for the broker password for the
> same reason. Neither decision was taken with publication in mind.
> **What publication still owes is disclosure, not secrets**, and it is
> recorded in the ADR so the deferred sitting starts from evidence: **26**
> private project names in the estate fixtures, **38,774** lines of
> narrative about a private box, the hostname in **8** test fixtures, and
> the commit address on all 347 commits. A history rewrite was refused —
> **116** backticked commit SHAs are cited across this repository's
> documents, plus `aad8236` in alfred's own message, so scrubbing the
> address spends every cross-repository reference to buy nothing.
> **Alfred's second observation is deliberately not answered here**: that
> four remote-less repositories score 100/100 while a stale branch costs
> five points. That is estate-manager's scanner, and this repository
> judging the estate's scoring of itself is *the monitor must not own the
> things it monitors* read backwards. Suite **3900**, unmoved — the
> sitting added no test, because what it added is a remote and a
> decision. No restart: nothing the daemon imports changed.

> **Two specimens outlived their producer, and only one of them was ever
> a specimen** (2026-09-09, Session 204, the documentary half of estate
> message `56752625` / their ADR-0140). Their commit retired
> `settings_unparseable` and `settings_not_an_object` from check 11 and
> named two things in this tree carrying the first string, leaving the
> call here. The handoff offered a dichotomy — *a regression guard
> against the codes returning, or a specimen asserting a shape nothing
> can emit* — and **it fits only the fixture**.
> **`tests/fixtures/estate_audit_wiring.json`'s `truncated` entry is the
> guard, and the deciding fact is that it cannot be re-recorded.**
> Measured rather than argued: their `run_check` driven at `b080ab1`
> from `estate-manager/service`, against the same 40-byte truncation of
> the live `settings.json` their message describes, returns
> `findings: 0` and `status: error`. So re-recording — the obvious
> tidy-up — writes an empty findings list into the specimen, and
> `test_a_file_level_finding_is_no_longer_judged_here` refuses an empty
> specimen in its own premise; the tidy-up would convert a guard into a
> test that announces it asserts nothing and goes on passing.
> **What it guards is live, and it was falsified rather than asserted.**
> Reintroducing the defect turns that test red **and**
> `test_no_title_matches_another_surface`, because the row carries
> `WIRING_FILE_TITLE`, which `judge_hook_wiring` mints from the local
> read: one title, dedup keeps one row, and the two surfaces' sweeps
> then disagree about when to close it. The structural test was not
> expected and is the stronger of the two.
> **The parametrisation is neither, because the question does not reach
> a constructed contradiction.** Its rows pair a `code` with a `detail`
> shape that contradicts it, which was unemittable *before* the
> retirement as well as after; the code string is a label chosen to
> disagree, never a recording. The code-reading mutation kills **both**
> rows, and a live code would weaken it, since `hook_wired_undeclared`
> genuinely carries an `event` in `detail` and the pairing would stop
> being one.
> **Both stand and both are marked, so the question is not re-opened a
> third time.** The real defect found was prose in the present tense
> about another repository's retired code — `SNAG-DOCS-001`'s shape —
> and the one substantive repair is a sentence born broken in `270e401`,
> `judge_audit_wiring`'s file-level comment having read *"and it is
> deliberately / this is a decision rather than an oversight"* with a
> lost clause, in the code implementing this very decision. Suite
> unmoved at 3900: the sitting added no test, because what it decided is
> that two existing ones stay. Daemon restarted on 2026-09-10 at
> **18:18:57**
> — **a reboot, not a deploy**, and nothing in this repository asked for
> it: a clean stop at 18:08:58 and a boot at 18:18:43, read off
> `last reboot` rather than inferred from the gap. The box came up on
> `6.18.49-2-lts` where the previous boot was `7.2.3-arch1-2`, which is
> the known shape of a kernel upgrade invalidating `LoaderEntryDefault`.
> Checked and it was not a monitoring gap: `CRITICAL_SIGNATURES`
> declares **both** amdgpu spellings, the LTS one and the `>= 7.2` one,
> so the GPU-reset predicate reads the same on either kernel — recorded
> because "checked, and it was not this" is a different fact from "never
> checked" and a later reader cannot tell them apart otherwise.

> **The payload carries no cause, so the row stopped claiming one**
> (2026-09-09, Session 203, the behavioural half of estate message
> `56752625` / their ADR-0140). `judge_audit_invariants` said an errored
> check's dimension *"produced no findings because nothing looked, not
> because nothing is wrong"*. Their commit made a `settings.json` that is
> **present, readable and broken** set `CheckResult.error` instead of
> filing a finding, so the sentence became false for exactly that case —
> and this family fires at `DEFAULT_SEVERITY`, which is this box's
> `tray.notify_min_severity`, so the wrong sentence would have become
> **audible** on the first 05:00 run after their commit.
> **The handoff called it "distinguishing error causes on a payload whose
> shape the estate owns", and there is no cause to distinguish.** Driven
> through the producer's own `CheckResult.as_summary()` on both surviving
> error arms **at one path**, the summary that read the file and found it
> broken and the summary that could not open it at all are
> **byte-identical outside the prose** — same `status`, same `findings`,
> same `inputs`. `inputs` is what a reader reaches for and it cannot
> serve: their `run_check` sets it *before* the first early return,
> deliberately, so an errored check says which file it could not use as
> readily as a clean one says what it compared against. The summary has
> four keys and only `error` says why.
> **So the narrowing is to stop asserting a cause and name the reason the
> producer already wrote** — a string this module had been fetching for
> its *truthiness* and discarding, which is `SNAG-UNITS-004`'s defect and
> `judge_queue_invariants` rule 4's remedy. Splitting that prose to
> recover a cause is refused for `monitor/collation.py`'s reason: it is
> free text the estate owns and reworded on the day this was written.
> What survives is the structural claim, true of every arm — *the
> comparison did not happen*, their own words, so the dimension is
> unjudged rather than clear.
> **The caps are about a notification body and `details` is not one.**
> `ERRORED_REASONS_LISTED` (2) bounds how many reasons the message names
> before the count becomes the news — `judge_attention` rule 1 a third
> time, ten of thirteen checks being able to error at once — and
> `CHECK_ERROR_CHARS` (300) is a **backstop above the measured
> population**, not a reading budget: the producer's three arms compose
> 141, 175 and 228 characters and an `ast` walk of its 24 `result.error =`
> sites finds a largest static composition of 170. `details.check_errors`
> carries every reason whole, however many and however long.
> **Ten mutations driven and each red on the intended test — and three of
> the eight new tests cannot be reached by a source mutation at all**,
> being driven at producer-captured fixtures, so they were falsified by
> mutating the fixture instead: a field that *would* discriminate the two
> arms, the two arms captured at two paths, and the cap dropped below the
> measurement. **Verified live** against the running estate: the clean
> box judges nothing, and the same live envelope with each error arm
> substituted renders 400 and 327 characters naming the estate's own
> sentence, where both would previously have said nobody looked.
> `SNAG-BRIEF-003` is the filed residue — every reason opens with the
> path and closes with the fault, so `truncate_at_word`, which keeps the
> head, makes the one cut this message can make the wrong one; empty
> population on today's measurement. Session 203 restarted the daemon at
> 08:17:20 on 2026-09-09, PID 3181664 → 3387306.

> **Half of estate-manager's `wiring` check crosses the seam, and moving
> all of it would have restored nothing** (2026-09-08, Session 201,
> [ADR-0008](../adr/0008-the-file-half-of-the-wiring-check.md), closing
> estate message `ecceab5e`). The owner recommended the whole check move
> here, because their ADR-0132 now lets an estate session write
> `settings.json`'s `hooks` key and the check therefore audits its own
> writes. **The recommendation is aimed at the comparator and what lost
> its independence is an operand**: the check compares the hook scripts'
> `estate-hook-event:` declarations against `~/.claude/settings.json`,
> ADR-0132 made the second of those estate-writable, and relocating
> `run_check` leaves both operands theirs. Today's `dotfiles` commit
> `54247f8` is the specimen rather than a hypothesis — an estate session
> built `memory-index-notice.sh`, wrote its declaration, wrote the
> matching `Stop` entry, and the estate's own check reported **0 findings
> with all six hooks `WIRED`**; run from here against those same two
> files it reports 0 too. *Correct, green and inert*, which is ADR-0006
> §2's own phrase for the shape it refused. **So the split falls at the
> inputs**: `settings_unparseable` and `settings_not_an_object` read
> `settings.json` **alone** and are `sysadmin/estate/hook_wiring.py` now,
> judged on a **sixth surface**; the two per-hook codes need the estate's
> declarations, stay theirs, and are still judged here off
> `GET :8400/api/audit/findings`. **Two clauses of ADR-0006's six-clause
> admission test were falsified the same morning by the other half of
> ADR-0132** and are corrected in the same commit — `~/.claude/settings.json`
> is a **symlink** into `~/projects/dotfiles`, registered `status: active`
> today, so *"in no repository at all"* is false, and *"repairable only by
> the owner"* went with the hooks-key narrowing. The decisive clause held
> and was re-measured: this module is still the only consumer of that
> endpoint outside the estate's publisher, and `dotfiles` carries
> `docs/roadmap/` and **no** `docs/adr/`. **A sixth surface, and ADR-0006
> §7's refusal is superseded by its own stated reason** — *"it arrives in
> the same payload from the same HTTP call"*, which it no longer does; so
> `audit_findings`' wiring pattern narrows to
> `Estate hook % not wired for %`, because a pattern left wide would let a
> successful pull of 8400 resolve a row raised from the local filesystem.
> **The live drive found what no fixture would**: the fault sentence
> stated its position twice — *"Unterminated string starting at **at**
> line 671"* — because several of json's messages already end in "at", so
> `str(exc)` is used and the hand-composed form removed; **estate-manager's
> check carries the identical doubling**, reported back rather than filed.
> **Eleven mutations driven and eleven killed by the test written for
> each**, checked by failing-test *name* rather than exit status.
> `SNAG-ESTATE-009`'s test needed widening and the verdict was measured
> either side first — all **29** `check-snag-claims` verdicts
> byte-identical, so a premise gone too narrow and not a control the fix
> broke. `SNAG-CFG-007` is the residue: two readers of one file, and a
> disagreement about *which* file invisible from both sides.
> Session 202 restarted the daemon at 22:37:03 on 2026-09-08, PID
> 2707546 → 3181664, to deploy the widened resolution guard, and
> **verified live**: the first `estate_judge` run afterwards, at
> 22:38:06, reports `surfaces_read` of **six** with `by_surface`
> carrying `hook_wiring: 0` and `unread_surfaces` empty — zero because
> this box's `settings.json` parses, not because nothing looked, and the
> empty unread map is what tells the two apart (`ports_checked`'s rule).

> **The predicate ADR-0007 settled is built, and the rendering it asks
> for is a command flag that would have re-timed ten timers**
> (2026-09-08, Session 200, `SNAG-GPU-001` implementation half closed).
> `services.yaml` gains `holds_vram:` on `llama-server` and
> `venture-chat` and deliberately not on `venture-embed`;
> `sysadmin/monitor/gpu_context.py` is the predicate;
> `_check_http_and_unit` records `degraded` with the whole derivation in
> `details['gpu_context']` when a declared unit's start instant is
> strictly earlier than the newest `CRITICAL_SIGNATURES` reset row.
> **The next action said to add `ActiveEnterTimestamp` to
> `get_unit_status`'s property list and that would have cost ten timers a
> spurious firing.** `--timestamp=unix` is a *command* flag, not a
> per-property one, so it also re-renders `LastTriggerUSec` — measured,
> `Tue 2026-09-08 04:31:09 BST` becomes `@1788838269` — and
> `_observed_fires` reads **any change in that token as a firing**. The
> property and the flag are therefore gated together behind one
> parameter that only the declaring caller passes, so every other
> invocation is byte-identical; a live test drives the real binary and
> fails if the flag ever escapes. The never-fired sentinel was
> **measured rather than assumed** and is unaffected: a timer that has
> never fired renders empty under both. **The floor is what makes the
> read affordable and no behavioural test can see it** — unfloored the
> grouped read is a parallel sequential scan at **69,810 buffers, 64,007
> of them reads**, and floored at the unit's own start instant it is an
> index scan at **6,855 all-hit buffers**, ~15 ms; the floor is exact
> rather than a bound, because a reset older than the start makes the
> predicate false by definition. A row-count bound was **refuted by the
> table**: **49,527** kernel rows sit newer than the newest stored reset,
> against **173** distinct messages, so grouping bounds it and a count
> never could. **The read runs inside a savepoint although it writes
> nothing** — it happens before the per-service savepoint and the run's
> transaction is already open, so an aborted statement would have cost
> every later service its row; a live test drives a statement PostgreSQL
> really rejects and the red names `InFailedSQLTransactionError`.
> **Fifteen mutations were driven and one stayed green** — deleting the
> SQL floor — so the statement is lifted out and compiled by a test,
> which is `abandoned_runs`' `IS NOT NULL` conjunct a second time.
> Verified live and **untriggered**: both declared services restarted
> after the last stored reset, so the counterfactual against a synthetic
> row is the only thing that could prove the wiring, and it does.
> `SNAG-GPU-002` is the residue — strictness removes only the *exact*
> tie, whose population is empty by construction, while the truncation's
> error window is a **full second**.

> **The state a GPU reset opens has no owner because it was never a
> state, and one live service refutes the declaration that describes it**
> (2026-09-08, Session 199,
> [ADR-0007](../adr/0007-a-poisoned-gpu-context-is-a-predicate.md)).
> Session 197 filed, and Session 198 carried forward, the question of who
> owns the state a GPU reset opens and who closes it, noting that a second
> owner of a service's health lifecycle is the defect this repository has
> found at seven scales. The question presupposed a state machine. *"This
> service holds a GPU context created before the last reset"* is a
> **predicate over two instants the box already publishes durably** — a
> unit's start instant from systemd, and the newest declared reset row in
> `log_entries` — so nothing opens it, nothing closes it, and every poll
> recomputes it: the unit's automatic restart moves the first instant past
> the second and the next poll reads false with nobody having been told.
> The owner is therefore the service check that **already writes the row**,
> and the second-owner defect is avoided by construction rather than by
> argument. **Falsified against the whole retained journal**, 2026-08-05 →
> 09-08 and **12** resets: on the two units holding VRAM the separation is
> total both ways — **6 of 6** and **10 of 10** aborts anticipated with a
> lead of 0.06 h to 9.78 h, against **0 of 11,565** successful requests
> served while the predicate was true. **The declaration's own reason is
> wrong in words**: it says *"any resident inference server alike"*, and
> `venture-embed` runs with no offloaded layers, holds no VRAM, and served
> **267 of its 823** successful embeddings while the predicate was true —
> so the population is a declaration in `services.yaml`, not a role, which
> would have shipped 267 false alarms. The recorded reading is `degraded`;
> **`unwatched` was refused on the code**, because that value means nobody
> looked by declaration and would drop the row from the reliability rates,
> excusing an outage as a decision. *No code changed and no restart is
> owed; the register's `SNAG-GPU-001` keeps its implementation half open.*

> **The memory index was repaired and the estate ruled on it the same
> morning, and the ruling's own finding is that the last two repairs went
> unrecorded** (2026-09-08, Session 198). The per-repository memory index
> the harness auto-loads into every session here went **25,638 → 20,690
> bytes** with **all 109 entries kept**, every title and link target
> byte-identical, the longest line **379 → 200** characters and **81 → 0**
> lines over 200. Only the one-line hooks were rewritten, and every figure
> in every new hook was checked against its own topic file first, so this
> was a delete of a duplicate rather than a move of detail. Session 197 had
> left the file over budget on purpose while its filing awaited a ruling;
> estate message `d409a9e8` was closed by estate-manager at **08:20:59Z**
> with the owner's ruling, their ADR-0131 and a sixth estate hook. Their
> sweep caught this repository repaired at **03:54** while the ruling was
> being taken — *"both repositories have now silently repaired and neither
> recorded a decision, which is the condition being ruled on, observed a
> third time"* — which is this repository's own argument in the filing
> landing on the filing. **The convention shipped as total size and the
> per-line cap the harness advises was refused on measurement**: across all
> **323** index lines on the box a 200-character cap flags **58** lines in
> **five** repositories that never breached and **zero** in the two that
> did, because the driver is entry count. The trim satisfies it anyway at
> **84.8 %** of a 24,400-byte limit, against a hook that warns at 90 %.
> **Three figures this repository published were corrected**: the breach
> began 2026-09-04T21:32:59Z rather than a day later, there were **nine**
> warned sessions and not seven, and "24.4KB" reads 24,400 decimal or
> 24,986 binary with nothing settling it, so the filing's *6 of 109 entries
> invisible* was an upper bound. **The one question handed back was
> measured and the answer is nothing** — the estate's hook count moves five
> to six and nothing in this tree pins it, swept across every `*.py`,
> `*.sh`, `*.md` and `*.yaml` for a numeral adjacent to "hook" with two
> unrelated hits. Message `7e187981` was closed at **09:46:58Z** carrying
> that measurement, the inbox is **0 open**, and the `hooks.Stop` entry
> that arms the new hook is the owner's under estate ADR-0024 and will be
> added through estate-manager, so tomorrow's `warn / hook_not_wired`
> finding is the intended delivery path and not a regression. *No code
> changed and no restart is owed; what moved inside the checkout is this
> block's own unresolved-alert claim, stale before the sitting began.*

> **The second headless region was a copy of a copy, and a residue called
> empty was measured at one region of two** (2026-09-07, Session 196). The
> 2026-08-07 capability-audit preamble standing above `## Fixed Issues`
> asked that its twelve defects be kept out from under a `###` sub-heading
> so `count_open_snags` could see them. They were fixed 2026-08-10 and are
> archived under exactly that sub-heading, and every one of the paragraph's
> four sentences has a second statement — the two that read as unique are
> near-verbatim in `tasks.md`, and its heading rule is `SNAG-ROADMAP-002`'s
> own Cause bullet sixty lines up in the same file, stated there with the
> measurement this paragraph omits. Retired outright: nothing moved, so
> there was nowhere to point that was not already in the file.
>
> **The rule it states is still live, and that was driven rather than
> read.** It cites `roadmap._sections`, and `count_open_snags` has since
> moved to `estate-lib`. At a synthetic register a `###` under
> `## Open Issues` still takes the count **2 → 1**. What lost its referent
> is the instruction, not the mechanism.
>
> **Sweeping the class rather than the specimen is what found the
> finding.** There were **two** headless regions, not one: Session 195's
> pointer, and this preamble carrying **1** bolded span into the *closed*
> `SNAG-DB-003`. So `read_entries`' docstring, shipped the same day, called
> the residue *empty* having counted the pointer it had just written and
> not the region eight lines below the entry it was measuring — corrected
> in place, with the instrument that would have caught it. Nothing
> published moved: **144** rows at **27** open and **108** entries at
> **27** open both ways, with `SNAG-DB-003`'s body **23 lines → 14**.

> **The movement log moved, and the test the handoff set would have
> answered it the wrong way** (2026-09-07, Session 195). It asked whether
> `snag_list.md`'s headless movement-log region should be retired behind a
> pointer or given a reader, on the test *does any sentence state something
> no check derives*. Almost every sentence does — they are per-sitting
> write-ups full of mutation counts and refuted hypotheses — so that test
> says *wire a reader*, which is what `check_movement` already refused in
> writing. What decides it is duplication, the estate's own rule: **85 of
> the 85** `SNAG-*` ids the region names exist as entries here, **88 %** of
> its distinctive identifiers and figures appear elsewhere in this document
> and **90 %** counting `HANDOFF.md`, and its most durable-looking
> paragraphs restate `sysadmin/snag_claims.py`'s own rule list.
>
> **The copy had already disagreed.** One undated present-tense paragraph
> said ten entries name a check and fourteen do not, against a live reading
> of twenty-five and two that `sysadmin-check-snags` prints at every run,
> and cited `SNAG-ESTATE-014` as live when it closed on 2026-08-27. The
> sentence was attributed rather than rewritten — `SNAG-TEST-011`'s remedy
> for the same shape.
>
> **Moved to `docs/sessions/movement-log.md` with a pointer where it stood,
> and nothing published moved with it**, measured either side rather than
> assumed: estate-manager's `read_snags` reads **144** rows both ways and
> `read_entries` reads **108** entries both ways. What corrects is
> `SNAG-SYSD-008`'s body, from 247 lines carrying 469 bolded spans to 25
> carrying 55. The pointer is deliberately neither a bullet nor bolded — a
> bulleted pointer adds a phantom row to the figure the estate board
> publishes, and a bolded figure in it rebuilds the defect at one
> fifty-eighth scale.
>
> **And a claim written into the moved file was refuted by driving it.** It
> said the fold was inert only because the entry's own status bullet
> preceded the region; `STATUS_FIELD_RE` requires a *bulleted* status, so an
> entry declaring none followed by prose that spells one still reads
> nothing. Inert by construction and not by ordering — corrected in the
> moved file and in `read_entries`' docstring, which described the region in
> the present tense.

> **The narrow rule is refused too, and the corpus it was measured over
> was a third not-an-entry** (2026-09-07, Session 194). The handoff asked
> whether an open entry carrying a standing figure should have its check
> actually *read* that figure, and set the trigger: refuse if most such
> figures sit in entries whose check answers a different question. Across
> the **25** checked entries there are **31** standing figures and the
> covering check re-measures **7** of them. **24 of 31** answer a
> different question — the trigger met, and met under either hand, since
> a generous classification gives 27 of 40. Building it means writing 24
> new measurements whose only consumer is a document's prose.
>
> **The denominator Session 193 published was wrong and the reader is
> why.** `read_entries` ends an entry at the next top-level bullet, and
> `snag_list.md` carries a headless region of unindented paragraphs — the
> per-sitting movement log — between the open entries and the closed
> ones, so every bolded figure in it is folded into whichever entry
> precedes it. `SNAG-SYSD-008` appeared to carry **83** figures and
> carries **25**. **58** of the 166 — **35 %** — are in no entry at all,
> so the entry population is **108**. The 28-against-138 split cannot be
> rescaled, because it was recorded as a total and never as members: a
> hand judgement whose members are not written down cannot be re-run,
> which is `SNAG-ESTATE-012`'s own point turned on the measurement that
> cites it.
>
> **The refusal survives and one of its three arguments does not.** Dated
> still dominates at **70.4 %**, which is *below* the 15-in-19 bar the
> handoff set — so the ratio no longer clears the trigger it was offered
> against, which is exactly why Session 193 declined to rest on it. The
> two arguments carrying no judgement are untouched.
>
> **One live pair existed and its remedy was one word.** `SNAG-TEST-011`
> stated a standing exposure in the present tense while its own check
> prints the live figure in the detail `claude-preflight.sh` renders at
> the start of every sitting. It is a sentence reading standing while
> meaning *at that commit*, so the instant was attributed rather than a
> guard built. Three further pairs a generous hand adds all say *"live on
> the day it shipped"* in their own sentence.
>
> **And it is the one rule here no guard could enforce**, which finally
> separates it from rule 11. That rule is syntactic and a reader can
> decide it; whether a check re-measures the quantity an entry states is
> semantic, and driven as a number match over the 25 checks it errs in
> both directions at once. No entry filed, no code beyond three
> docstring and prose corrections, tests unmoved.

> **Rule 11 stops at the Quick Status table, and the register refuses it
> harder than the Notes column did** (2026-09-07, Session 193). The
> handoff asked whether the totality rule should also reach
> `snag_list.md`, and said the measurement had to come first. It did, and
> it answers cleanly: across the **27** open entries, read through rule
> 11's own `status_figures` and this repository's own `read_entries`,
> there are **166** bolded figures — **28** are quantities the box could
> still be asked for today and **138** name a past observation. That is
> **83.1 %** against the 15-in-19 that refused the Notes column, so the
> rule is refused on the axis the handoff nominated, by a wider margin.
>
> **Askability is not enforcement, and the generous reading was measured
> too.** Asking only *"is there a procedure runnable today that yields a
> comparable number"* clears **85** of the 166. Three were re-asked
> against the box and every one had moved with no entry wrong for it: the
> suite figure one entry states as `2532 passed` reads 3819 today, `67
> entries` reads 108, `101 / 18` reads 108 / 27. A Quick Status figure is
> current by construction; an entry's is a finding dated to the sitting
> that took it, and re-measuring one is noise rather than enforcement.
>
> **The ratio's own margin is thin, which is why it does not decide it
> alone.** The classification is a hand judgement — deciding that an
> English sentence states a current quantity is the job
> `SNAG-ESTATE-012` says a human has to do — and only **7** of the 166
> would have to move from dated to standing for the share to fall below
> the 15-in-19 bar. It takes **55** to fall below a bare majority, so
> what is robust is that dated *dominates*, not that it clears that
> bar. The two arguments below carry no judgement at all.
>
> **What decides it is a type error the ratio hides.** **17** of the 166
> are an instant or a date rather than a count — `19:50:19`,
> `2026-09-17` — and **15** more are one half of a before-and-after
> movement, `17 → 18`. The Status column has no member of either class,
> so the reader is not merely over-firing on the register, it is
> **mis-typed** for it: nearly a fifth of what it would report is not a
> measurement of anything, and a totality rule surfaces those first
> because they are precisely what no pattern reads.
>
> **The register is already total on a stronger axis.** `check_convention`
> reports every open entry no check names — **2 of 27** today, both of
> them the documentation entries about this very question. A snag check
> asks whether the *condition* still obtains, which is a register's
> question; this rule asks whether a *figure* is current, which is a
> dashboard's. Stacking the second beneath the first would report 138
> stale-looking figures that are not stale.
>
> **What is refused is the totality rule, not checking a snag figure.**
> The **28** standing figures are real — `0 of 31` services still set
> `auto_restart`, re-asked and unmoved — and the **25** registered checks
> are that claim already honoured entry by entry. No code shipped and no
> entry was filed: declining to widen a rule is a decision, not a defect
> left unfixed. It is recorded in `quick_status_rows`' docstring and in
> `SNAG-DOCS-010` because a decision with nothing recording that it was
> taken is `SNAG-CFG-001`'s shape. No guard ships either, and that is
> argued rather than skipped: a guard pinning "this rule was not widened"
> answers the same way for ever, which is `check_review_schedule_unread`'s
> recorded defect, and one over the snag corpus would empty on the next
> snag edit. Tests unmoved.

> **The Status column is total now, and the handoff's own axis was the
> wrong one** (2026-09-07, Session 192). Rule 7's `unclaimed` finding
> enumerates `CLAIM_PATTERNS`, so it reports a figure some pattern
> already reads and is structurally blind to a figure with none — the
> blindness that let the suite count sit unclaimed in the Quick Status
> **Status** cell for eleven sittings. Rule 11 makes that column total: a
> bolded figure there must be claimed by a pattern-bearing check named on
> its row.
>
> **The handoff asked for "total over the table *rather than* over
> `CLAIM_PATTERNS`", and replacement loses three quarters of the
> enforcement.** Driven at the live document with each marker deleted in
> turn, rule 7 fires for all four — `routes`, `tables`, `migration_head`,
> `tests` — and the new rule fires for `tests` alone, because **only one
> of the four figures is in the Status column**. The handoff's
> parenthetical that it is "where every current claim's headline figure
> lives" is false: `routes`, `tables` and `migration_head` are all in
> **Notes**. So the rule is additive, and both findings share the
> `unclaimed:` prefix so one sweep still finds either.
>
> **The naive rule was refused by measurement and the alternative by one
> live row.** The table's 12 rows hold **20** bolded integers — **1** in
> Status and **19** in Notes, of which **15** are history prose, because
> rule 1's "the whole file restates old figures on purpose" is true of
> that column too. Against the other candidate the corpus said nothing:
> over **239** revisions "the first bolded integer of each row" has 488
> observations to this rule's 97, zero false positives either way, and no
> disagreement across **263** marked-row observations. What refuses it is
> the **Database** row — two figures, two markers — so a row-keyed rule
> would let one marker exempt the other, trading figure-granular
> enforcement for row-granular in the silent direction.
>
> **The forward population is one cell and the entry says so.** In 239
> revisions the Status column has carried a bolded figure in exactly one
> row, so what this adds over rule 7 is "a Status cell gains a figure no
> pattern reads" — which has happened once. It is kept for
> `FROZEN_TABLES`' reason: the class has one member, the member is fixed,
> and deleting a guard with its last finding takes the guard against the
> defect returning.
>
> **Two claims the code makes are now testable rather than asserted.**
> The reader takes a bold *span* rather than a `**` followed by a digit,
> which agrees with the corpus at all 97 observations and cannot mistake
> a closing fence for an opening one — pinned on `**green**3807`, where
> the digits are not bold at all. And one span is one statement, so the
> live historical `🟡 **3011 green, 6 red**` is one figure and not two.
> `🟢 Phase 3 Complete` is excluded on purpose: the emphasis is already
> the convention separating a measurement from a name, so rule 11 is
> total over *bolded* Status figures and says which hole that leaves.
>
> Twelve mutations driven and twelve killed — **one only after the
> stand-in was repaired**: the "span, not fence" mutation was first written as a
> greedy `\*\*(.*)`, which agrees with the real reader on every input and
> so modelled nothing. Tests **3807 → 3819**. `SNAG-DOCS-010` is the
> residue: the Notes column cannot be made total, and its population is
> empty today because all four current Notes figures carry a pattern.

> **The suite figure is a claim at last, and the axis the handoff framed
> it on was the weaker one** (2026-09-06, Session 191). The Quick Status
> suite figure sat **inside** the region this checker parses and was the
> only bold figure in it carrying no pattern — rule 7's `unclaimed`
> finding enumerates `CLAIM_PATTERNS`, so a figure with no pattern is one
> it is structurally blind to. It had been wrong on 8 of the 11 sittings
> that measured it. `check_tests` reads it now and `measure_tests`
> collects the tree in 1.9 s.
>
> **The choice was ownership, not cost.** The handoff framed it as a
> trade between a 1.9 s collection and an 81.6 s run, on the premise that
> a check is affordable at both ends of a sitting. The two ends are
> **not symmetric**: preflight runs this checker and no suite at all,
> while the close runs it *and* `check-vacuous-guards.sh`, which already
> runs the whole suite and — since `SNAG-TEST-012` closed the day before
> — already raises an issue when it is red. So *green* has an owner, a
> second assertion of it here is the second-owner defect, and the cost
> would land exactly where nothing else is measuring it. The owner chose
> the collected figure; the cell is re-worded to name it, and names the
> close as the owner of green rather than leaving that silence to be read
> as an oversight.
>
> **The row states its figure twice and the handoff treated it as one.**
> One pattern spans both spellings, so drift between the Status column
> and the Notes is reported by machinery rule 2 already had — a
> single-spelling pattern would have agreed with whichever half was
> written first.
>
> **Every partial count is refused, and both shapes were measured.**
> `pytest --collect-only` prints `2 tests collected, 1 error` at exit 2
> and `1/2 tests collected (1 deselected)` at exit **0** — figures that
> look like answers and are zero-because-blind wearing one.
>
> **The cost was the surprise.** `snag_claims.ops_report` drives the whole
> of `check_all` over a synthetic document twice per probe, so an
> uncached collection ran ~40 times a run and took the suite **75.4 s →
> 151 s**. Cached per process it is 79.0 s, a net **+3.6 s**; the cache
> changes no behaviour, so it is pinned by a statement test.
>
> Eighteen mutations driven and eighteen killed, **three only after the
> test that should have caught them was repaired** — a clause hidden
> behind a gate it is multiplicative with, a substring test made monotone
> by an append-only document mentioning its own phrase 7 times, and a
> fixture whose strict `cache_clear` errored all 158 tests in the file
> instead of letting the statement test speak. Tests **3780 → 3807** (27
> added, none retired — **26 written and 1 generated**, the registry's own
> parametrised test, so this check sits inside its own population). Open
> entries **25 → 26** and entries carrying no check **0 → 1** — both
> `SNAG-DOCS-009`, filed rather than absorbed: `claim_sentence` cannot
> isolate a table row, measured at `HEAD` as well, and it carries no check
> because any drive showing a single row is a drive over the *fix*.
> `SNAG-ESTATE-012` is the other residue, and greenness is now one of its
> sentences by design.

> **The deploy claim swept files the daemon cannot run, and the fix is a
> walk of the source rather than the surface the handoff asked for**
> (2026-09-06, Session 190). `Daemon serves the code on disk` compared
> the newest `.py` anywhere under `sysadmin/` against the running
> process. Six of those modules are console-script entry points and
> alembic's `metadata.py`, each read fresh by a process of its own, so
> no restart of this daemon could make any of them less stale — and
> `sysadmin/snag_claims.py`, at 70 commits the most-edited file in that
> six, had held the claim red since the previous sitting.
>
> **Rule 4 had priced this in its own last sentence and priced it
> wrong, twice.** It called a file the daemon never imports a rare miss
> costing a `kill -TERM` that "is not privileged and takes a second".
> Measured: **50 of 191** commits touching this package touch only those
> six, so it is a quarter of the check's fires; `tasks.md` records the
> restart paid on **eleven consecutive sittings** "whose restart moves
> nothing a caller can observe"; and `SNAG-SYSD-007` is what the second
> claim was worth — five restarts in ten minutes trip
> `StartLimitBurst`, recovery needs a polkit challenge `sudo -n` cannot
> supply, and one of those five was this claim's. The box was down 77
> minutes. **Zero of the 191 commits are mixed**, so narrowing has never
> been able to mask a daemon edit riding along with a tooling one.
>
> **The handoff's stated blocker was true of a trace and false of a
> walk**, which is what made the cheap option available. It reasoned
> that a population keyed on `create_app()` drops
> `sysadmin/core/llm_client.py` — imported lazily inside three review
> functions, named at module scope nowhere — and concluded the
> measurement had to come from a running daemon over a new surface. A
> function-level `import` is in the AST as plainly as a top-level one:
> `daemon_modules` reaches **94 of 100** with no endpoint, no contract
> entry and no restart to bootstrap, and the walk is a strict superset
> of what a clean `create_app()` holds, differing by exactly that one
> module. The owner chose it over asking the daemon.
>
> **A newer file outside the graph is named, not swept** —
> `ports_checked`'s rule, because "considered, and no restart is owed
> for it" must not read like "nobody looked". The claim's first live
> output was about the file being edited to produce it.
>
> **Three clauses turned out to change no output, and all three were
> found by driving mutations rather than by reading.** The
> `__pycache__` filter in `daemon_modules` is excluded by reachability
> anyway; the `create_app()` call in the new check adds **0** modules
> because `import sysadmin.main` already holds 95; and the ancestry
> clause was *expected* to be redundant and is not — dropping it loses
> six `__init__.py` files no statement in this package names, because
> its job is package initialisation and not the attribute-versus-module
> reading its first docstring claimed. The two genuine no-ops are kept
> and pinned by **statement** tests, `abandoned_runs`' rule.
>
> **Four tests failed only under the whole suite**, and the premise was
> working. Other files import the review modules, which import the lazy
> module, so the new check refused to measure in a contaminated
> process — the same trap the sitting had already walked into by hand,
> importing the walker into the process it was measuring and reading its
> own import back as a finding. Twenty-one mutations driven and
> twenty-one killed. Tests **3752 → 3780** (28 added, none retired;
> baseline measured in a detached worktree rather than by stashing).
> Open entries **24 → 25**, `CHECKS` **24 → 25**, entries carrying no
> check unmoved at **0**. The residue is `SNAG-SYSD-009`: a lazily
> imported module is counted before the daemon has imported it, which is
> rule 4's accepted direction and never the reverse.

> **A red suite is not a measure that did not run, and the close said
> it was** (2026-09-06, Session 189). `SNAG-TEST-012` closed.
> `check-vacuous-guards.sh` collapses its exit-2 roads into one status
> and argues in writing that a red suite is not *its* finding — sound,
> and about that script. `claude-postflight.sh` discarded the
> distinction: every road rendered as *"The measure did not run"*,
> raising no `ISSUES`, and step 6's `else` — reached whenever the gate
> returned 2 **and** no code file changed — printed a green tick reading
> `No uncommitted code changes to test`. A docs-only sitting is not an
> edge case there, it is the population, and it is exactly the sitting
> that breaks a document guard.
>
> **The split is keyed on the producer's own sentence**, because the
> exit status cannot carry it and a fifth status would move the contract
> two other gates read. `SUITE_RED_MARKER` is a copy — a shell caller
> cannot import one — so it is pinned at **both** ends: the producer
> still emits it, no other road carries it, it sits between the pytest
> run and the coverage report, and the judge cannot speak it.
>
> **A red suite raises `ISSUES`** — the owner's ruling, and the question
> the entry left open in writing. The cost is stated rather than
> discovered: a sitting mid-way through fixing its own suite now hears
> about it at the close. The three genuine could-not-measure roads still
> raise nothing, which is step 3.9's rule one section down.
>
> **The entry's shape-of-fix was right and its arithmetic was one road
> short.** It named four roads to exit 2, which is the gate's own
> docstring; measured, there are **six** `exit 2` sites, and one of them
> — `mktemp -d` failing — prints nothing at all. That is why the
> discriminator is keyed *positively* on the red-suite sentence rather
> than negatively on the other three: an empty report falls to
> could-not-measure by construction. Only the silent road can see the
> difference, and it is the one mutation that reaches it.
>
> **The status gate is behaviourally redundant today and says so.**
> Widening it from the status that carries the roads to every status
> changed no output, because the finding branch is tested first at 3.8
> and the green branch wins at step 6, so a red-suite reading at exit 1
> is unobservable through both blocks. The clause is kept for
> `abandoned_runs`' reason — its visibility is what stops a later sitting
> reordering those branches — and pinned by a **statement** test, which
> is the only kind that can reach a clause whose removal is invisible in
> behaviour.
>
> **Two things only running it could have said.**
> `check-vacuous-guards.sh` names `coverage json` in the *prose above
> the code*, so the first structural pin found the paragraph rather than
> the invocation — the mention-vs-invocation trap
> `test_close_runs_the_handoff_guard` recorded for the other script, met
> in a second file. And the status gate's specimen is **not** the new
> test file, which carries the accessor rather than the literal, so the
> premise moved to the producer, whose report interpolates an assert's
> own source verbatim; the population of asserts naming the sentence is
> **empty today**, measured.
>
> Twelve mutations driven; **one passed against code this sitting
> expected to be broken** — the status gate, which is what turned it
> into a statement test. Tests **3733 → 3752** (19 added, none retired;
> baseline measured by collecting with the new file ignored, and
> 3733 + 19 = 3752 is the arithmetic rather than a total taken
> afterwards). Open entries **25 → 24**, entries carrying no check
> **1 → 0** — no check was ever written for this entry, so closing it is
> what retires the report — dispositions now `blocked 3, decided 16,
> delegated 5`. The detector outlives the entry:
> `tests/test_close_reads_the_guard_gate.py`, `FROZEN_TABLES`' rule.

> **The close runs the guard now, and the suite was already running
> there — which is not the same thing, and the difference is the entry**
> (2026-09-06, Session 188). `SNAG-TEST-005` closed.
> `claude-postflight.sh` step **3.9** runs
> `tests/test_handoff_shape.py` in **0.5 s** at the one moment
> `HANDOFF.md` has just been written, and raises `ISSUES` on its red.
>
> **The entry's own re-measurement that morning was true of a grep and
> missed a transitive run.** It read *"`claude-postflight.sh` runs those
> four `check-*.sh` and no pytest"*. Step 3.8's
> `check-vacuous-guards.sh` has run the **whole suite** under
> `coverage run --branch` since 2026-09-05 — Session 179, one day
> *after* this entry was opened — so the guard has been running at the
> close all along. It is not the fix, and the reason was driven rather
> than argued: a red suite is exit **2** there by that script's own rule
> 3, which `claude-postflight.sh` renders as *"the measure did not
> run"*, raises **no** `ISSUES`, and follows at step 6 with `No
> uncommitted code changes to test` on a docs-only sitting — which is
> exactly the sitting that breaks this document. Driven verbatim out of
> the shipped script at `GUARDS_STATUS=2, TOTAL_CODE=0`. The guard's red
> reached the reader as a blind measure contradicted by a green tick two
> sections later.
>
> **The check could not see the fix its own entry names, and had to be
> widened before it could be trusted to flip.**
> `check_handoff_shape_unguarded` swept `claude-precommit.sh` alone
> while the entry's cheap half lands at the *close* — a control a landed
> fix cannot move, which is `check_review_schedule_unread`'s defect. The
> widening refuted nothing on its own and that was measured at the
> moment of the change: neither script named `pytest` or
> `test_handoff_shape` on any executable line, so the verdict was
> **unmoved at `match`** with the sweep already reading both. The
> postflight line is what flipped it to `mismatch`.
>
> **Three readings driven at the shipped block**, extracted between its
> own markers rather than retyped, against a stub `pytest`: clean →
> quiet, broken → `ISSUES=1` naming the failed rule, absent
> `.venv/bin/pytest` → yellow and **not** a pass (`ports_checked`'s
> rule, since a bare `uv sync` prunes the dev extra and `uv run pytest`
> then falls through to `/usr/bin/pytest`). The red was driven at
> Session 164's real defect on a `.bak` copy of the live document, and
> **estate-manager's parser was the third-party witness**:
> `test_the_local_read_is_the_line_the_board_publishes` failed, so the
> board would genuinely have carried `something else entirely`. Document
> restored byte-identical, md5 checked.
>
> **The check retired with the entry and the detector did not** —
> `tests/test_close_runs_the_handoff_guard.py`, `FROZEN_TABLES`' rule —
> **and the sitting's own prose about why it is stronger was wrong until
> the counterfactual was driven.** It requires *both* names on lines
> that run something. With the call deleted and the two advice echoes
> left standing: the retired either-name rule reads `mismatch`; **the
> mention rule alone still reads `mismatch`**, because `if [ -x
> ".venv/bin/pytest" ]` is a real non-echo line; **requiring both names
> alone goes green**, because the advice echo carries the second name;
> only the pair sees it. Multiplicative rather than independent —
> `SNAG-AGENT-008`'s shape — and separable only at a stand-in, which is
> why `TestNeitherRuleCatchesTheRegressionAlone` is a recorded
> counterfactual and says so in its own docstring.
>
> **It caught this sitting's own handoff within a minute of shipping.**
> The Session 188 block went in *below* Session 187's, so `headings[1]`
> was `### The action Session 187 filed` rather than `## Next action`,
> and `test_it_is_the_first_heading_after_the_title` went red naming it.
> Not contrived and not the compound failure — their parser takes the
> first heading containing "next" wherever it sits, so the board line
> would not have moved — but it is that failure's first half, produced at
> the close by the sitting that had just shipped the guard for it.
>
> **One residue was filed rather than absorbed, and it is the general
> case this fix bought one file out of.** `SNAG-TEST-012`: step 6's
> `else` branch is reached whenever the gate returned 2 **and** no code
> file changed, so a docs-only sitting with a red suite is told `No
> uncommitted code changes to test` — true about its own subject and
> false about the reader's question. The neighbouring `elif` is wrong on
> one of the four roads to exit 2, and it is the road that matters: a
> red suite **did** run. It carries no check yet, so
> `convention:unchecked` reports it — rule 6 working rather than a gap
> being hidden.
>
> Nine mutations driven and nine killed, each on its intended tests.
> Tests **3722 → 3733** (17 added, 6 retired with the check) — **the
> baseline was measured by stashing to HEAD and re-collecting, against
> 3651 in this table's own cell**, a 71-test gap that is
> `SNAG-ESTATE-008`'s shape in this cell again and the reason the
> arithmetic is carried rather than the total. Open entries **25 → 25**
> — one closed and one filed, which a bare total hides — `CHECKS` **25 →
> 24**, entries carrying no check **0 → 1**, dispositions now `owed 1,
> blocked 3, decided 16, delegated 5`. One red in the first full run was
> the machinery working: the suite started before the register was
> edited, so `check_markers` fired on the `handoff_shape_unguarded`
> marker naming a check nobody implements. Its key is cited rather than
> reproduced here, because a quoted marker is a marker —
> `quoting-a-marker-rearms-it`, and this block sits inside the region
> `ops_claims` parses.
>
> **No restart is owed and the deploy check's `no` is again inherited
> from a `sysadmin/snag_claims.py` edit** — but this sitting stopped
> taking that on the static read. Session 187 confirmed it by finding no
> `from`/`import` statement under `sysadmin/` naming the module; that is
> a claim about the source, and what was wanted is a claim about the
> process. `create_app()` was built in a throwaway interpreter and
> `sysadmin.snag_claims` is **absent from `sys.modules`** afterwards, so
> the daemon does not hold the edited module at all. The AST read agrees
> — 0 imports, 7 docstring mentions — and is now the weaker of two.

> **The ranking was decided on which population is live, and the winner's
> own claim had to be measured before it could be ranked** (2026-09-06,
> Session 187). The register declared `owed 0, blocked 3, decided 17,
> delegated 5` and all **29** checks `still holds`, so nothing was
> closable and the choice fell to what is reachable. Every other
> `decided` P3/P4 states a **measured-empty population**
> (`SNAG-LOG-016`, `SNAG-LOG-017`, `SNAG-LOG-018`, `SNAG-SVC-005`,
> `SNAG-CFG-003`, `SNAG-UNITS-006` at 0 of 38 units) or a **remedy
> costing more than the defect** (`SNAG-TRAY-011` at 1.04 M rows a
> month, `SNAG-ESTATE-009` refused on cost and on correctness,
> `SNAG-SYSD-008` at 82.8 ms against `oom_kill 0`). `SNAG-TEST-005`
> moves `decided` → `owed`, P3.
>
> **The five `delegated` were ineligible and the three `blocked` could
> not move truthfully**, which a ranking has to say rather than leave as
> a silence. The estate rule that a question routed to the owner is
> answered by the owner keeps the first five where they are; and `owed`
> asserts work is owed **now**, so promoting `SNAG-AGENT-012`,
> `SNAG-AGENT-013` (still 0 open rows, 0 of 31 services) or
> `SNAG-SVC-001` (blocked on the owner) would assert a precondition had
> arrived when none has.
>
> **"Real and recurring" is a measurement and the entry carried none.**
> Bounded to the guard's own lifetime — `tests/test_handoff_shape.py`
> born at `30bfbea` on 2026-08-31 — **4 of the 57 commits touching
> `HANDOFF.md` since then ship a document the guard refuses**, all four
> consecutive sittings, 09-02 through 09-05. The unbounded sweep over
> all 209 commits says **30** and is 4× too flattering: 26 predate the
> guard and are the abandoned `## Next session — ranked` convention. The
> figure was reproduced, not counted — `git show 9558544:HANDOFF.md` into
> the tree fails `test_the_document_has_exactly_one_next_heading` with 17
> passing beside it, tree restored from a scratchpad copy.
>
> **One of the entry's two reasons for `decided` is refuted on the box**,
> and it is the one that made the fix look expensive: *"a change to a
> script two other repositories' conventions describe"*.
> `claude-postflight.sh` exists in **one** repository, this one, and
> neither the global rules nor estate-manager's `session-brief.md`
> contains the string `postflight` or `preflight` at all. The document is
> cross-repo; the script is not.
>
> **The ordering shipped by Session 186 met its first real case and was
> driven as a counterfactual.** The register edit and the line naming the
> entry are one commit, in that order. Reverting the word to `decided`
> refuses the identical line at **both** printers — the checker returns
> `??` and `test_the_next_action_names_no_entry_that_is_owed_nothing`
> goes red — each quoting `REFUSAL_REMEDY` in full, so the remedy was
> read by the sitting it was written for. Restored with a `.bak` copy
> rather than `git checkout`, which would have eaten the uncommitted
> disposition move.
>
> Open entries **25 → 25**, `CHECKS` **29 → 29**, entries carrying no
> check **0 → 0**, dispositions now `owed 1, blocked 3, decided 16,
> delegated 5`. **No code, no migration, and the fix is deliberately not
> taken here** — queue-only was put to the owner before any edit, because
> doing the work would have emptied the queue the action asked to fill.
> The deploy check's `no` is inherited from Session 186's
> `sysadmin/snag_claims.py` edit, confirmed again by an import-shaped
> read: **no `from`/`import` statement anywhere under `sysadmin/` names
> it**, all five mentions being docstring prose.

> **The cheap remedy, and the trigger the predecessor set was measured
> rather than argued** (2026-09-06, Session 186). `SNAG-TEST-011`
> recorded two candidates and left the choice unmade under a rule: take
> the cheap one — document the ordering, so the register edit moving an
> entry to `owed` ships in the commit that publishes the line — unless a
> real member of the ranking, reasoning or closing classes has appeared.
> **None had.** All **29** register checks report `still holds`, so no
> `decided` entry is closable and the closing class has no live member;
> `Snag list movement` reads `unmoved since 42d11fa`; and the line that
> put the question named an `owed` entry. A permanent fifth vocabulary
> term bought against zero live members is `NOISE_MIN_OCCURRENCES`'
> invented constant with a vocabulary's blast radius.
>
> **The ordering is documented in the refusal and not in a docstring**,
> which is `SNAG-DB-005` rule 6 measured rather than borrowed: `_REMEDY`
> held that outage's remedy all along and wrote it **only to the
> journal**, the surface nobody opens unprompted, and the 23 hours were
> spent by a reader holding a toast that did not carry it. The surface a
> sitting is holding here is the refusal itself, so `REFUSAL_REMEDY` is
> appended to `check_next_action`'s refusal note and the blocking test
> reads *that name* rather than retyping the sentence — one statement,
> two printers, pinned by a test asserting the consumer names the
> constant and does not contain its value.
>
> **The limit ships beside the remedy**, because the ordering is
> truthful only where a check is genuinely owed on the *defect*. The
> refusal names the three classes it cannot reach and names the entry
> they belong to. **The escape hatch was checked rather than assumed**:
> switching to the expensive remedy later is work on that entry's
> defect, so the sitting doing it makes a truthful `decided` → `owed`
> edit and the documented ordering carries it.
>
> `SNAG-TEST-011` moves `owed` → `decided` and **stays open** — the
> guard still cannot tell a correction from the remedy it refuses, so
> its check still reports `still holds` and all 29 verdicts are
> byte-identical either side of the commit. Five mutations driven, none
> passing against broken code; tests **469 → 474**. Open entries
> **25 → 25**, `CHECKS` **25 → 25**, entries carrying no check
> **0 → 0**. The register is left declaring **no `owed` entry**, which
> is its resting state and not a milestone — `owed` reads 0 on 33 of the
> 41 commits touching the file since the population was created, so the
> first draft of the next action calling it a first was refuted by the
> file it was about. **The deploy check reports a restart owed and none was taken**:
> the only module edited is `sysadmin/snag_claims.py`, a console script
> nothing under `create_app()` imports, which is the false positive
> `ops_claims` rule 4 prices in writing.

> **The guard is right and has a blind spot, and the corpus that looked
> like evidence answered a confident zero** (2026-09-06, Session 185).
> `check_next_action` refuses a published next action naming a `decided`
> or `delegated` entry, which is what it is for. Work on the **entry**
> rather than on the defect — correcting its ranking, correcting the
> reasoning of its refusal, or closing it — is owed precisely while the
> word says otherwise, and the guard resolves ids and never intent.
> Filed as `SNAG-TEST-011`, `owed`, carrying a check of its own.
> Open entries **24 → 25**, `CHECKS` **24 → 25**, entries carrying no
> check **0 → 0**. The count is a movement and not an ordinal: a check
> retires with its entry, so *"the Nth check"* is a measurement taken at
> write time — `SNAG-DOCS-006` already says twenty-fifth, truthfully.
>
> **All three costs the handoff asserted were reproduced rather than
> quoted, and reproducing them is what corrected the premise.** Session
> 183's red was reconstructed exactly — the inherited line at `4caf59e`
> against the register at `23fd601` returns `unknown`, one of one
> refused. Session 184's line at `5fdf73e` describes its entry in prose
> and never names it. What the sentence got wrong is *"the one kind of
> work"*: correcting a ranking, correcting a refusal's reasoning and
> **closing** an entry have the same shape, and in all three the
> `decided` → `owed` → `decided` workaround is a false assertion, since
> `owed` asserts a check is owed and none is. Closing is not
> hypothetical — `SNAG-SYSD-003` went `Open — decided` to closed within
> the hour on 2026-09-02.
>
> **The obvious instrument answers zero and the zero is not evidence.**
> Resolving every next action in `HANDOFF.md`'s history against the
> register at that commit gives **0 refusals in 176 lines**, which reads
> as no defect. `tests/test_handoff_shape.py` blocks the commit, so a
> refused line cannot reach the corpus: every instance was paid for at
> authoring time and erased. Zero-because-avoided, never
> zero-because-clean — `ports_checked`'s rule arriving inside the
> instrument a first sitting reaches for. The standing exposure the
> corpus cannot show is **21 of 25 open entries**.
>
> **The check asserts indistinguishability, never refusal**, because a
> check asserting the guard refuses a `decided` entry reports `ok` for
> the life of the guard and goes on reporting it the day the distinction
> lands — `check_review_schedule_unread`'s defect, twice now. It drives
> a synthetic four-specimen register, one per disposition, so no live
> document reaches the verdict and a register holding no `decided` entry
> does not refute it. Eight mutations driven and **one passed against
> code this sitting expected to be broken**: narrowing the refusal to a
> single word moves the check's population with the guard and still
> reports `match`, which is correct — the claim is that ids resolve
> where intent does not — and is now pinned as a test rather than left
> as a coincidence.
>
> **Session 183's red is deliberately not filed**, because finishing the
> work a line names is what reddens the predecessor's line and the
> remedy is to rewrite the handoff, which the sitting does anyway; its
> one real cost, that nobody hears the red, is `SNAG-TEST-005` and
> already owned. **The deploy check reports a restart owed and no
> restart was taken**: the only module edited is `sysadmin/snag_claims.py`,
> which is a console script nothing under `create_app()` imports, so
> this is the false positive `ops_claims` rule 4 prices in writing and a
> `kill -TERM` would deploy nothing.

> **The register's last unchecked entry has its check, and the counter
> reads zero for the first time** (2026-09-06, Session 184).
> `SNAG-LOG-016` declared `decided` while carrying none, which under
> Session 182's rule asserts that a check is *unwritable* — and the
> entry's own refusal bullet is that assertion, costing *"is the live
> population non-empty"*. Every word of it is true **of a population
> check**, and a check reproduces the **defect**: the identical
> mis-costing `SNAG-TEST-010` made the same week.
> `check_payload_reword_unselected` is the twenty-third check and
> reports `still holds`. Open entries carrying no check: **1 of 24 →
> 0**, by a check being written. Disposition `decided` → `owed` →
> `decided` inside one sitting, and the round trip is committed apart so
> that the correction is a commit rather than a sentence about one.
>
> **The instrument is split where rule 7 splits it, and neither half
> would do alone.** What the guard *says* — its selector, its statement,
> the relation that statement reads, the source it filters on, its
> placeholder — is read out of the file with `ast`; what its code *does*
> is driven in PostgreSQL, by running that same statement with its
> `FROM` retargeted at a five-row `VALUES` corpus. Nothing is retyped
> and nothing is read from `log_entries`, so **no reset need ever have
> been stored** — which is rule 1 and the whole of the correction.
> Answering *"would this line have been selected"* with `needle in
> message` is a second implementation of `LIKE` that agrees with today's
> pattern by coincidence of its shape and with no other; live, both
> genuine kernel prefixes select and neither payload reword does.
>
> **Four controls, each forbidding a verdict rather than reporting
> one.** A declared spelling the declaration no longer holds is
> 2026-09-04's defect and not this entry; one the selector does not
> admit means the selector is not the one the drive thinks; an
> *unrelated* line it does admit means it discriminates nothing and
> would admit a reword for the worst possible reason; and a reword the
> declaration already covers is not the row the guard exists to catch.
> The corpus is literals **vouched for by production** —
> `CRITICAL_SIGNATURES` must hold both genuine spellings and neither
> reword — and the skip is pinned apart from the selection, because the
> mechanism is two claims and SQL reaches only the first.
>
> **The corpus cannot tell the entry's stated closure from a widened
> `LIKE`, and that is deliberate.** Both admit every reset line and
> neither admits the boot line beside them, so the check watches whether
> a reword reaches the comparison and cannot be satisfied by the shape a
> fix arrives in; rule 2 leaves judging which one landed to the reader
> of a `mismatch`. Thirteen mutations driven and thirteen killed —
> **one only after a test was repaired**: a fixture that is gone and a
> fixture that has stopped skipping both leave the note naming the
> fixture, so asserting the name was an assertion two readings satisfy,
> and collapsing the two branches left it green.

> **The entry that carried no check now carries the twenty-second, and
> the witness is the figure the entry was wrong about** (2026-09-06,
> Session 183). `SNAG-SYSD-008`'s durable claim is a **missing
> discriminator**: `GET /api/sysadmin/services/sysadmin-service/details`
> serves `MemoryCurrent`, and that number cannot separate `anon` from
> page cache. `check_memory_decomposition_unserved` drives the route,
> reads the figure back through `ServiceDetailInfo`, compares it against
> the cgroup of the pid that same payload named, and then asserts that
> nothing under `sysadmin/` or `sysadmin_tray/` opens `memory.stat`.
> Live: **453.9 MB served, of which 67 % is page cache**, and no reader.
> Open entries carrying no check: **2 of 24 → 1**, by a check being
> written. Disposition `owed` → `decided` the same day — now carrying a
> check rather than asserting unwritability by silence.
>
> **The served figure is what stops the check passing by finding nothing
> at all.** A report that nothing serves the decomposition, taken on a
> box where nothing serves anything, is a dead surface wearing this
> entry's sentence rather than evidence for it — so an absent, unusable
> or divergent figure is `unknown`, never `match`. Two further roads to a
> false emptiness are closed separately: the sweep must also find
> `MemoryCurrent` itself, **excluding this module from its own
> evidence** (it names the property in a constant, so a witness counting
> its own spelling would be satisfied by itself on the very day the
> surface stopped naming it), and `memory.stat` must actually carry
> `anon` and `file` before their absence from a route means anything.
>
> **A source sweep answers a claim about routes, and only a source sweep
> can.** `systemctl show` publishes `MemoryCurrent`, `MemoryPeak` and
> `MemoryAvailable` and not one of them separates anon from cache, so a
> route serving the split has to open the file — the entailment that
> makes the sweep sufficient. The obvious instrument is worse than
> imperfect, it is blind: the route serving the witness declares **no
> `response_model` at all** (the contract registry files it *parse-side
> only*), so a walk over `create_app()`'s response models cannot see the
> very surface the entry is about. `RssAnon` is out of scope by the same
> discipline — `/proc/<pid>/status` decomposes a *process*, which the
> entry's own first bullet measures apart from the cgroup's.
>
> **Fourteen falsifications, each landing on its own branch**, eleven of
> them ways of not-knowing — and one of them was vacuous until
> `vacuous_guards` said so. The assertion that the check's own file is
> absent from the **readers** list ran over an empty population, because
> after the exclusion it always is; moved to the sweep it found the
> stronger claim underneath, that **without the readers-side exclusion
> the check reports `mismatch` against its own entry on its first run**,
> off its own `memory.stat` constant. The fix stand-in is a **real module** in a
> synthetic tree rather than an injected finding, because a stand-in
> modelling only the defect cannot tell a check that measures from one
> wired to a constant; the docstring-only twin beside it is the
> detector's own falsification, and it matters here because the entry,
> the roadmap and three docstrings all name `memory.stat` in prose.

> **`decided` with no check is legitimate, and it is the only place the
> register can say *never* rather than *not yet*** (2026-09-06, Session
> 182). Rule 6's counter and the disposition vocabulary were read as
> disagreeing — 0 owed against 2 unchecked. They do not. The counter
> reports a fact about **freshness** (these N claims are only as fresh as
> the last hand sweep); the disposition reports whether that staleness is
> **chosen or pending**. `SNAG-ESTATE-014` filed exactly this gap on
> 2026-08-27 — *"cannot tell 'not yet' from 'never' — `ports_checked`'s
> rule at the level of the register rather than the reading"* — after
> refusing both `<!--check:none_yet-->` and a `covered-by` bullet. The
> disposition vocabulary landed **five days later** and is the missing
> discriminator, and nobody had connected them. `owed` + no check is *not
> yet*; `decided` + no check is *never*.
>
> **So the binding rule is not that every unchecked entry is `owed`.**
> `SNAG-TEST-010` read `owed` because a check *was* owed and turned out
> writable — that is *not yet* resolving correctly, not a precedent that
> the counter is a queue. What `decided` + no check asserts, in addition
> to the condition being settled, is that a check is **unwritable** — and
> `SNAG-ESTATE-014`'s judgement already set the form that assertion takes:
> named by the finding it is about, with no marker, **and with the reason
> stated in the body**. Silence is not the argument.
>
> **Both of the two failed the rule, and the handoff's two candidates were
> both wrong.** It offered *the disposition is right* or *the same
> mis-disposition `SNAG-TEST-010` carried*. The true third for
> `SNAG-SYSD-008` is that the entry's stated reason for staying open is
> **refuted by the box**, so the question of its check is downstream of a
> correction it owed first.
>
> **The refuted claim, in two commands.** It read *"no health surface
> reads the unit's own cgroup — the one number that would have ranked
> this in a minute is served nowhere"*, having checked
> `/api/sysadmin/self` and `/api/sysadmin/resources` and stopped.
> `GET /api/sysadmin/services/sysadmin-service/details` serves
> `MemoryCurrent: 453611520` against the cgroup's own `memory.current` of
> **453287936** at the same moment; `ServiceDetailInfo.memory_current` is
> in this repository's contract registry, and `services_tab.py` renders
> it — the tray has been printing **`Memory: 433 MB`** on this daemon's
> own card the whole time. A claim of the form *nothing serves X* is
> refuted by one route, and this one was filed from the two surfaces a
> reader would think of rather than from `GET /openapi.json`.
>
> **What replaces it is sharper than what was filed.** The number that
> *is* served is `memory.current`, which the entry's own first bullet
> proves cannot separate `anon 155 MB` from `file 298 MB` with every byte
> of the file half cold and reclaimable. So the surface served the figure
> that **opened** this entry as a 462 MB "resident set" and not the
> decomposition that settled it. The durable half is a **missing
> discriminator**, not a missing surface — `memory.stat`'s `anon`/`file`,
> unserved and measured so — and it is checkable, which is why the
> disposition moved `decided` → `owed`. Register either side:
> `decided 16` → `owed 1, decided 15`, unchecked unmoved at **2 of 24**.
>
> **`SNAG-LOG-016`'s refusal is mis-costed too, and it was left alone
> deliberately.** Its bullet costs only the *population* check — *"is the
> live population non-empty"* — which is the identical mis-costing
> `SNAG-TEST-010` made and Session 181 refuted: a check reproduces the
> **defect**, not the discriminator. Driven in real SQL against a
> synthetic corpus, no writes and no live reset: both genuine kernel
> prefixes select, a payload reword does not, so the guard skips on
> exactly the row it exists to catch. That is writable in a sitting and
> moves when the entry's own stated closure — an event-keyed population —
> lands. Not written here, because the register's own shape-of-fix rule is
> one check per sitting.

> **The entry that said it could carry no check now carries the
> twenty-first, and the reason it gave was refuted by its own sitting**
> (2026-09-06, Session 181). `SNAG-TEST-010` said a check would have to
> reproduce the *discriminator* the arc measure lacks. It does not — it
> reproduces the **defect**: a probe under the real
> `coverage run --branch` in which two comprehensions run their loop
> while their element never evaluates, and `_loop_turned` answers
> **turned** for both. `check_element_never_ran_reads_turned` is that
> probe, at **80 ms** warm, and it reports *still holds* against the
> shipped measure. Open entries carrying no check: **2 of 24**, down
> from 3 — by a check being written, not by an entry closing.
>
> **The population is invisible, which is a second reason counting was
> never available.** `SNAG-LOG-017`'s *reproduced, never counted* rests
> on a measured-empty population that refills; this one rests on
> something stronger. A blind site reads as **healthy** — the same
> string a site whose element provably ran comes back with — so nothing
> reports it and there is no set to sweep even in principle. Session
> 180's 311 of 881 is a bound on where the defect could hide, never a
> list of anywhere it does, and the check asserts that identity of
> answers rather than describing it.
>
> **The witness is a third party, and that is what makes the check
> writable at all.** Establishing *the element never ran* from the arcs
> would be reading the evidence the measure reads and agreeing with it
> by construction. So the probe's element appends to a list and each
> shape asserts that list **inside itself**: the interpreter answers the
> premise, and a failed premise takes the drive non-zero, which reads
> `unknown` rather than as a measure that has learned to separate them.
>
> **Two controls, each forbidding a different verdict.** An empty
> *outer* iterable must still read *did NOT turn*, or a `_loop_turned`
> answering `turned` for everything — the single worst regression the
> measure has — would satisfy this check perfectly and the entry would
> read as holding hardest on the morning its own instrument broke. And
> an element that provably ran must read *turned*, because that is what
> makes `turned` the healthy answer the blind shapes are
> indistinguishable **from**. Either control failing is `unknown`: that
> is `SNAG-TEST-009`'s rules having moved, a different fault, and one no
> sentence about vacuity may absorb.
>
> **The instrument is `_loop_turned` and deliberately not `sweep()`.**
> The entry's mechanism is stated about that function; `sweep()` folds
> in the report join, the freshness test and the mtime test, so a moved
> verdict could not say which layer moved — and the signal there would
> be an **absence**, a blind shape failing to appear among the findings,
> which is the weakest shape a claim can take. Driving a private name is
> the trade `check_incident_fold_splits_at_a_poll` already makes on
> `LogAggregatorAgent._execute`: a rename lands in this repository's own
> commit.
>
> **The fix stand-in separates one shape only, and that is the sharper
> drive.** The entry named the filter shape and Session 180 added the
> nested one, so a check keyed on both moving together would report a
> half-landed fix as though nothing had happened. Eleven drives, each
> landing on its own branch, six of them under the real tool because the
> probe costs 80 ms where the sibling gate costs ninety seconds.
>
> **The premise was marked and the marker came straight back out, which
> is the correction this sitting owes another convention.**
> `@pytest.mark.premise` discharges `test_live_drive_premises.py`'s rule
> 2 for the **whole file**, and `test_snag_claims.py` is in that rule's
> population for its *database* reads — twenty-odd drives exempted in
> `PRE_CONVENTION` on the habit that each asserts its own not-knowing
> branch. A witness about a coverage subprocess would discharge all of
> them, *"and this module could not tell"* — that constant's own
> wording, written about a different candidate mark and true of this one
> for the same reason. Its tripwire named the file within one gate run.
> The premise assertion stayed and is ordered first; only the marker
> went, and `PRE_CONVENTION` now records that the argument is about
> **whose** witness rather than about a static walk.
>
> **A next action that names no entry makes another guard vacuous, and
> the guard said so within one gate run.**
> `test_handoff_shape.py`'s refusal test filters the SNAG ids the
> published line names, and this sitting's line names none — so
> `check-vacuous-guards.sh` reported its comprehension as having run
> over an empty population. Empty is the healthy reading there, and what
> is indistinguishable from it is a **reader that finds nothing in a
> line that carries something**: neither of that class's two premises
> witnessed `read_named_entries` itself. So it is fixed rather than
> filed — a third premise drives the reader at a synthetic line over the
> real register, and the comprehension carries a `may-not-turn:` naming
> it. Falsified: with `read_named_entries` returning `[]` the premise
> goes **red and the refusal test stays green**, which is the blind pass
> it exists to catch.

> **The disposition moved `owed` → `decided`, which is what the register
> was counting.** What was owed was the check, by rule 6; the
> *discriminator* was refused and ranked by Session 180 and remains
> unattempted — the honest candidate is an arc into the element line
> that is not the loop's back-jump. The entry stays **open** because the
> measure is still blind, not because anything is queued. That moved the
> published next action into `check_next_action`'s refusal set the
> moment the disposition changed, which is the guard doing exactly its
> job and is fixed by this sitting's handoff.

> **The fourteen undecidable sites are gone, and the entry that
> replaced them names one shape when there are two** (2026-09-05,
> Session 180). `scripts/check-vacuous-guards.sh` reports **865 of 881**
> comprehension sites turned, with **no undecidable block at all** —
> exit 0, suite green at 3651. The old 851 plus the 14 is exactly the
> new 865, so every site that was refused now reads as having turned.
>
> **Undecidability is a property of the tree, not of the run**, which is
> what made the fix cheap. All three refusals in `_loop_turned` are
> syntactic — an element on the comprehension's own first line, two
> comprehensions sharing an element line, two generator frames on one
> line — and none reads an arc. Driving the real function with an
> **empty** arc set therefore enumerates the same fourteen the
> ninety-second gate names, so each candidate reformatting was settled
> statically at no cost and the suite run was spent confirming the
> answer rather than finding it.
>
> **Ten locations, and the nested one is the trap.** Six had an element
> on the first line with the clauses spilling below; four were pairs
> sharing an element line, reported twice each. For
> `all(any(d in c for d in denials) for c in clauses)` the outer
> element **is** the inner comprehension, so moving the outer element
> down lands it exactly on the inner's own line and trades one refusal
> for the other — measured, not guessed. Both had to drop a line. The
> three adjacent pairs took a bound name instead of a hanging bracket,
> which leaves each comprehension alone on its line and reads as
> ordinary test code.
>
> **`SNAG-TEST-010`'s upper bound is 296 of 881 sites carrying an `if`
> clause** — and **311** once the second shape is counted, leaving
> **570** for which the measure is exact. That last number is the one
> the entry could not state and the one that ranks it.
>
> **The entry names a filter and the mechanism is wider.** A
> comprehension with more than one `for` whose inner iterable is empty
> for every outer item is blind identically: no filter is involved, the
> element never evaluates, and the detector answers *turned*. What both
> shapes share is that the loop turns **without the element running**.
> Established with a witness rather than read off the arcs — the
> fixture's element appends to a list and the fixture asserts that list
> is empty **inside itself**, with an empty *outer* iterable beside it
> answering *did not turn* as the control that stops the drive agreeing
> with itself.
>
> **So the entry's reason for carrying no check is refuted too.** It
> said a check would have to reproduce the discriminator the measure
> lacks; the witness fixture reproduces the **defect** instead, in about
> two seconds, which is this register's *reproduced, never counted*
> idiom. One is writable and is not written here — this sitting was
> asked to measure and to close the fourteen. Open entries carrying no
> check reads **3 of 24** off `sysadmin-check-snags`, so Session 179's
> handoff saying `3 → 4` is the stale half of a disagreement its own
> entry had already settled.
>
> **The cost is stated rather than implied**: nothing in this repository
> runs a formatter, so the ten reformatted sites stand — but a
> comprehension has no magic trailing comma, so adopting `ruff format`
> would collapse every one of them back onto a single line and rebuild
> the fourteen in a commit that changed no logic.

> **A guard that ran over nothing is visible now, and the rule the
> entry left behind was wrong** (2026-09-05, Session 179).
> `SNAG-TEST-009` is **fixed**. `coverage run --branch` on the run the
> gate already makes, the arcs read out of the `.coverage` SQLite with
> stdlib `sqlite3`, and `sysadmin/vacuous_guards.py` judges whether each
> comprehension under `tests/` turned. No second pass, no
> `sys.monitoring`: the cost the whole question turned on does not
> exist.
>
> **Rule 1 as the entry records it reports a loop that turned zero times
> as having turned.** *Some arc runs backwards inside the span* is
> satisfied by a generator's **exhaustion return**, which arcs from the
> `for` line to the frame's own first line whether or not the loop ever
> turned. What discriminates is the **element** line — a comprehension
> is written element-first, so a turn arcs from the iteration back into
> the element — with the entry arc excluded, and excluded only where the
> element sits below the first line, since where they coincide no such
> arc exists and excluding it would discard the self-arc that is the
> whole signal for every single-line comprehension.
>
> **Fourteen sites cannot be decided either way, which the entry does
> not record and its detector counted as turned.** Two written shapes
> leave a turning loop and an empty one **byte identical**: an element
> on the comprehension's own first line, and two comprehensions sharing
> an element line — nested or merely adjacent. Neither guess is safe, so
> they are named on every run and **move no verdict**, the remedy being
> a reformatted test rather than a fixed guard. The live drive asserts
> the **arc sets are equal** rather than that the answer is `None`, with
> a decidable pair beside it as the control.
>
> **`meta.has_arcs` is the fail-closed gate and the one this could most
> easily have shipped without.** A data file written without `--branch`
> opens cleanly with an empty `arc` table, so read as evidence it says
> every comprehension in the suite ran over nothing — *hundreds* of
> fabricated findings out of a missing flag, and unreachable by a row
> count. Asked-for-and-unreadable is `unknown`; not asked for is a
> narrower measure that says so.
>
> **The standing declaration is corrected rather than kept.** The block
> this replaces published **323 of 6334 asserts across 53 files** as the
> unjudgeable population; the arc measure ranges over **865** sites, of
> which 6 sit in an assert *message* and are excluded, **828** turned,
> **14** are undecidable, **1** was never reached and **16** are
> findings — reproduced independently and matching the entry's triage
> exactly.
>
> **The verdict on those is taken: one fix, fifteen declarations.**
> `tests/test_tray/test_config.py:365`'s
> `assert all(path == "tray" for path in report.unwalkable)` became
> `assert report.unwalkable == []`, which is decidable *and* stronger.
> The rest carry a `# may-not-turn:` reason — a second marker, because
> one marker for both halves would report every loop declaration as a
> stale assert declaration on every run.
>
> **The declaration anchor was wrong, and it shipped green.** A loop
> declaration was read from the comprehension's *enclosing statement* —
> right for an assert or an assign, wrong for the `return {…}` in
> `tests/test_message_backfill_live.py` that holds six, where one comment
> covered all six and four came back *declared and turned anyway*. Exit
> **0** throughout, because a stale declaration moves no verdict; the
> only thing that named it was the stale report the module's docstring
> argues for. Anchored on the comprehension now, stopping at its own
> first line so a marker inside a nested comprehension is not read as
> the outer one's claim.
>
> **Fourteen mutations driven and fourteen killed**, each on its intended
> tests, including the entry's own rule 1, which reddens four — one of
> them the live drive. The live half runs the real tool at 0, 1 and 2
> iterations, `any`, `next` and both undecidable shapes, because the
> entry's own history (**110 → 43 → 26 → 23** findings) is a detector
> that returned a plausible number every time it was wrong. **Three
> reds were self-inflicted and the arithmetic caught it**: stashing a
> test file to measure its baseline *while the gate was collecting* made
> the gate run the old file, and 3611 + 36 = 3647 reconciled it exactly.

> **The gate the entry owed, and a declaration is what keeps it
> readable** (2026-09-05, Session 177). `SNAG-TEST-006` is **closed**.
> `scripts/check-vacuous-guards.sh` runs the suite under an ephemeral
> `uv run --with coverage` overlay and `sysadmin/vacuous_guards.py` joins
> that report to an AST walk of `tests/`, refusing an `assert` a green
> suite never evaluated. Exit **0/1/2** for this run's clean / found /
> could-not-measure, wired at `claude-postflight.sh` as section 3.8.
>
> **The module never imports coverage, and that is load-bearing rather
> than tidy.** The tool is not a dependency here and stays out of
> `.venv` — measured at **107** packages and a clean lock either side,
> re-taken rather than borrowed, because the entry's figure of 122 was
> against an environment that had drifted fifteen packages off the lock.
> A judge that imported coverage would be untestable on every box in
> this estate; instead the join is a `coverage json` report read with
> `json`, so all **33** of its own tests run on synthetic trees.
>
> **The comprehension half is a standing declaration and not a fourth
> status**, as Session 176 settled. Every report ends with **323 of 6334
> asserts across 53 files** carrying a comprehension whose truth over an
> empty iterable is `True` with the line executing — `ports_checked`
> literally, a field on every payload carrying whether the measure
> looked, driven at all three verdicts.
>
> **All six live findings were legitimately unevaluable, so the gate
> ships with six declarations rather than red for ever.** Three branches
> on an idle estate, one on a wiring check with no whole-file finding,
> and two deadline guards a fast box satisfies before the loop turns
> once — that pair cannot be restructured into evaluating at all. Each
> carries a `# may-not-evaluate:` reason, `known_noise`'s rule 2: the
> reason is required, the set is named on every run, and a declaration
> whose assert *did* evaluate is reported too, because a stale exemption
> stops describing anything and starts hiding the next finding.
>
> **The staleness rule was found by the fix on itself.** Writing those
> declarations moved every assert below them without changing one
> statement — the shape a digest of the executed set cannot see — and
> the sweep named all three edited files against a report twenty minutes
> old. The same edit settled the ordering: counted **after** the skips
> the standing declaration fell **314 → 312** the moment those files
> went `moved`, reading as a suite with fewer unjudgeable asserts rather
> than as a sweep that stopped looking, so the blind count is taken
> before all three.
>
> **Three of twenty-two falsifications passed against deliberately broken
> code**, and the three are distinct shapes. The ordering specimen
> nested *downwards*, so breadth-first came out `2, 4, 6` — already
> sorted, asserting nothing; the live shape is a nested assert written
> first and walked last, which produced `166, 167, 147`. The fail-open
> test covered **one of two roads**: `str(None)` is `"None"`, truthy, so
> an absent timestamp reached the *unparseable* branch and a mutation to
> the absent branch passed cleanly. And one "mutation" was a **different
> correct implementation** rather than a break.
>
> **The first live run read one declaration of six, and nothing here
> could have caught it.** Five went in as multi-line comment blocks with
> the marker at the *top*, and the reader looked one line above the
> assert — so the gate refused five asserts whose author had just watched
> themselves declare them, which is worse than having no declaration rule
> at all. Every synthetic fixture used a **single-line** comment, the one
> shape that cannot discriminate the rule. The reader takes the whole
> contiguous comment block now and the reason continues onto its
> following lines; the gate reports **6 of 6** and exits 0. That fix gave
> the empty-reason rule a second return path and the existing test
> covered one of them — the two-roads shape for the second time in one
> sitting, after `str(None)`.
>
> **The check retired with the entry and its detector did not.**
> `check_vacuous_guard_ungated` is refuted by exactly the hop it was
> built to see and is gone with 226 lines of tests and five constants;
> `TestTheGateIsOnTheClosePath` outlives it. The gate's **first** live
> run returned **2, not 1**, on a tree being edited underneath it — the
> red-suite rule working before anything depended on it. The residue is
> `SNAG-TEST-009`, filed with **no check** for the opposite reason to
> the two entries that carry none on cost: its instrument already runs
> at every close, since the gate prints the count on every report.
>
> **`uv sync --all-extras` prunes an undeclared editable install, and a
> cross-repo pin went red rather than quiet.** The documented sync
> removed `_editable_impl_estate_service.pth`, which is in no lockfile;
> `test_the_local_read_is_the_line_the_board_publishes` gates its skip
> on the **tree** rather than the import for precisely this, so it
> failed instead of passing on a box where the pin no longer existed.
> Restored with `uv pip install --no-deps -e`; the other thirteen pruned
> packages are imported by nothing here, checked rather than assumed.

> **A gate-reading check answers what the gate would cost to run**
> (2026-09-05, Session 176). `SNAG-TEST-006` gains its check — the
> twenty-first, and the first move that entry named for itself. Driving
> the sweep is what it rules out on cost: the honest instrument is the
> suite under coverage, and `check-snag-claims.sh` runs at both ends of
> every sitting. What is cheap and refutable is whether anything on the
> close path invokes coverage at all, which is
> `check_handoff_shape_unguarded`'s idiom one script over and for the
> same reason — a measure that is documented and not wired. Live: six
> scripts, 257 invocation lines, four guards, zero coverage
> invocations. Open entries with no check, three to two.
>
> **Three departures from the check it borrows from, each forced by this
> entry's fix having a different shape.** The fix here is a *new script*
> wired at `claude-postflight.sh`, whose own name carries no coverage
> token, so the sweep is **one hop** — a read of the two roots alone
> reports `match` over exactly the thing it watches for, and removing
> the hop turns one test and only one red. **Mentions are dropped as
> well as comments**: both roots name a guard on an `echo` while
> `claude-postflight.sh` prints "Consider running your test suite" and
> runs none, so a sweep over executable lines would be refuted by the
> sentence describing the gap. And **both roots are read**, because a
> gate wired at either closes the entry.
>
> **The mention rule changes no verdict today, and that is measured
> rather than left to imply otherwise.** It drops 132 of the two roots'
> lines, two of them naming a guard the script does not run and **none**
> naming a coverage token. What it buys is the shape the file's own
> idiom makes likely next — advice added as an `echo` — and the empty
> population is pinned by its own test instead of being dressed up as a
> live catch.
>
> **The third verdict is decided and it is not an exit status.** A gate
> reporting "no vacuous guards" while blind to `assert all(f(x) for x in
> live)` is `ports_checked`'s rule broken inside its own fix, so the gate
> owes a reading of the half line coverage cannot reach — and the shape
> it owes is a **standing declaration on every run**. Exit 0/1/2 keeps
> `check-migrations.sh`'s meaning, because each is a property of *this*
> run that a sitting can act on. The comprehension blindness is a
> property of the *measure* and is permanent: re-measured at 3566 tests,
> 309 of the suite's 6275 asserts carry a comprehension across 52 files,
> unmoved from Session 173's count. A status firing on that fires for
> ever, which is `SNAG-LOG-002`'s binary confidence — a report pinned at
> "could not tell" for a fortnight and read by nobody — and a permanent
> warning nothing can clear trains the reader to dismiss the family.
> Until the gate exists the check carries the fact in its `mismatch`
> note, so whoever lands a two-verdict gate is told at the moment they
> would otherwise close the entry.
>
> **Two of eight falsifications passed against deliberately broken
> code**, and they are the two shapes this repository keeps finding. One
> mutation was a **no-op** — the replacement string did not match the
> source, so the test it was aimed at had nothing to be red about, and
> the drive was scripted to assert its own edit afterwards. The other
> asserted a **value** where it meant provenance: `PRECOMMIT_SCRIPT in
> CLOSE_PATH_SCRIPTS` is `==` on `Path`, so restating the path as a
> literal is indistinguishable from borrowing the constant. `is`
> discriminates, because a fresh `Path` is a fresh object. Every drive
> above patches `CLOSE_PATH_SCRIPTS` wholesale, so no mutation of it is
> observable behaviourally at all — that fact is what the statement test
> exists for.

> **A stub is a stated premise, and these two were stating it by leaving
> a hole** (2026-09-05, Session 175). `SNAG-TEST-008` is **closed**.
> `tests/test_alert_dedup.py` and `tests/test_service_write_isolation.py`
> drive `SysAdminAgent._execute` with the session, the service list and
> five checks stubbed, and left the estate read real — so eight
> otherwise-hermetic tests dialled 8400 from inside the method under
> test. Each stubs `read_arbitrated_stops` at the **transport** now and
> declares `_NO_ARBITRATION` as the reading its assertions hold under.
> Forty-four connections to none.
>
> **Patching the method out was the cheaper shape and reaches the right
> answer for the wrong reason.** It leaves `_arbitration` at `None`, and
> the raise falls through `or _NO_ARBITRATION` to the same reading —
> spelled as an *absence*, where `None` and `unread` are both empty and
> only one of them says which. That is `ports_checked`'s rule at the size
> of a stub, and it is the constant's own argument: "nobody asked" must
> never be spent as "the estate holds nothing". Stubbing the transport
> instead leaves the memo gate, the config leaf and the borrowed client
> real, so the only forged thing is the hop that would have left the box.
>
> **"Which reading tests more" had nothing to choose between, and only
> driving it said so.** Six cells — unread, idle and a lease naming every
> unit spelling in sight, each with and without the fixtures'
> `systemd_unit` forced non-`None` — leave nineteen of nineteen passing
> in all six. A witness over `_raise_judged` proves the granted cell was
> not inert: twenty-one judgements moved from `critical` to `info`
> carrying `stopped_by_estate: True`, and no assertion moved. So the
> entry's stated reason for the immunity — a `kind: http` entry having no
> unit for a lease to name — is refuted, and the immunity is a property
> of what those files assert on rather than of their fixtures.
>
> **Two of the entry's own figures were wrong and the instrument was
> why.** Its cost of sixteen connections per suite run counted *distinct*
> addresses per nodeid; every connect is forty-four across the eight
> tests, so the clock cost on a box that drops packets rather than
> refusing them is 2.75x what was filed.
>
> **Pinned by identity, not by the reading string**, and the
> falsification is what settled that. The production reader builds a
> fresh `ArbitratedStops` on every call, so `is _NO_ARBITRATION` fails on
> any box; comparing `reading` does not. Measured while removing each
> stub in turn: 8400 is up here and the real read answered `idle`, so a
> value comparison is red here and **green while dialling** on a box
> where the estate is down. With either stub removed the other nineteen
> assertions stay green, which is what makes the two new guards the only
> thing holding the fix.
>
> **The blind spot it was filed under now has an empty population, and
> that is recorded rather than deleted.** A test file whose connection is
> made *for* it by production code carries no token, and no sweep over
> `tests/` can reach it — that is still true. What changed is that
> nothing holds the property: connecting files fell from fourteen to
> twelve, and the four holding no spelling to the two that were always
> reconciled. The entry closes with **no check**: its honest instrument
> is the whole suite under a socket probe, which runs at both ends of
> every sitting and cannot afford one, so the per-file identity tests
> outlive the finding instead.

> **A convention's population decides what it can ask for, and this one
> was asking a DSN** (2026-09-05, Session 174). `SNAG-TEST-007` is
> closed. The premise rule refuses a live drive carrying no
> `@pytest.mark.premise`, over a population that was the `_live` glob
> plus "the file spells a connection string" — so it under-read on
> **both** of its own axes, and the sharper miss was the database one:
> `test_abandoned_runs.py` says in its own docstring that it drives the
> live database inside a rolled-back transaction, and it was invisible
> because it goes through a helper.
>
> **The obvious HTTP widening was measured and refused.** Matching
> `http://localhost:<port>` the way the DSN rule matches a connection
> string does not transfer, and the reason is what the fix rests on:
> nothing in this tree *models* a DSN — a fake database is spelled
> `sqlite:///` — while a loopback URL is exactly how a fake service is
> spelled here. Fourteen files carry one with a port and four connect to
> it, so the literal rule reports ten stand-ins. A name whose job is to
> dial cannot be written by accident, and the four in `_LIVE_HANDLES`
> reach six of six connecting files with no false positive.
>
> **The instrument was a socket probe, per nodeid, across a green full
> suite** — the same shape Session 173 used coverage for, and chosen for
> the same reason: it answers directly whether a connection happened
> rather than asking an AST walk to guess. Fourteen files connect; four
> hold no token, and all four are reconciled rather than counted.
>
> **The tripwire refused a handle within one test run**, which is the
> part worth carrying. `query_one` looked like the obvious member — it is
> the reader every registered snag check goes through — and it is named
> in exactly one file, as the string inside `patch.object`. A name whose
> only appearance is a stub is the *opposite* of evidence: it marks the
> connection being taken out.
>
> **Two of the six owe nothing, and that was driven rather than read.**
> `test_alert_dedup.py` and `test_service_write_isolation.py` reach the
> estate through an unstubbed fail-open call inside the method under
> test, so they carry no token and no sweep over `tests/` can reach them.
> Forging the producer's own `ArbitratedStops` three ways — unread, a
> lease holding nothing, and a lease naming every unit spelling in sight
> — leaves nineteen of nineteen passing in all three, because a
> `kind: http` entry has no unit for a lease to name. Filed as
> `SNAG-TEST-008`, whose cost is the clock and only on a box unlike this
> one: an estate that drops packets rather than refusing them turns a
> 0.35 s pair of files into some minutes of ten-second timeouts.
>
> **One mutation of nine survived and bought a test.** Deleting the
> clause that reads a *qualified* use broke nothing, because every handle
> in this tree happens to be imported by name today — so the clause was
> carried by a coincidence in the current tree, and `import ops_claims`
> plus `ops_claims.check_all(...)` was a way out of the rule that nobody
> would have chosen and nothing would have reported.

> **A guard that asserts nothing is green, and the suite is the last
> thing able to tell you** (2026-09-05, Session 173). The sweep Session
> 172 asked for is done, and the instrument is the part worth keeping:
> coverage over a green full suite, then an AST walk mapping every
> unexecuted line back to the statement enclosing it. At 3538 tests,
> **8** `assert` statements under `tests/` had never once been evaluated
> and **0** `for` loops had never iterated.
>
> **The founding shape had moved on, and the one live instance was
> somewhere nobody was looking.** The prediction guard that opened this
> hunt now runs — the block gained its first `expires` member on
> 2026-09-04 — so the sweep found its successor instead.
> `test_a_live_wiring_finding_still_separates_its_two_events` filters the
> estate's audit findings down to the `wiring` check, a family that has
> filed **nothing** in its whole history, so its three assertions had
> never executed. Its docstring said so to the reader; nothing said so to
> the runner.
>
> **The premise reports and never refuses, which is the opposite of its
> sibling's.** Zero wiring findings is the estate's hooks being correctly
> wired, so failing on an empty population would turn a healthy estate
> into a red suite — the calendar writing a failure. What must not pass
> unnoticed is the other road to zero: the producer *retiring* the check,
> which reads exactly like a clean run. `last_audit.checks` separates
> them, which is `ports_checked`'s rule asked of another repository's
> audit.
>
> **Direction is the whole discrimination.** A `for` missing the arc
> *into* its body never iterated; one missing the arc *out of* it always
> returned early — the ordinary shape of a helper walking an AST and
> returning its match. Both are spelled "partial branch", and read
> without direction this sweep reports thirteen findings of which twelve
> are wrong.
>
> **Two limits are filed rather than implied.** `SNAG-TEST-006`: nothing
> here can see the next one, and line coverage cannot see the second
> shape at all — `assert all(f(x) for x in live)` is true over an empty
> `live` and the line *executes*, so the **309** asserts here carrying a
> comprehension needed a hand sweep, ten of them over a live iterable.
> `SNAG-TEST-007`: the premise convention's population is a DSN literal,
> so the file holding this finding owed nothing — and neither does
> `test_abandoned_runs.py`, whose own docstring says it drives the live
> database.

> **The `expires` family has its first live member, and measuring the
> boundary moved it by a day** (2026-09-04, Session 172). `SNAG-LOG-014`
> predicts its own residue away — four rows purged on `ingested_at` — and
> states the moment as a *date*, which a fixed-hour purge turns into an
> instant. The newest copy was ingested at **19:50:19** on 2026-08-17, so
> thirty days lands that evening, *after* the 03:00 purge of 09-16 has
> already run. Driven at the real `purge_statement` against the live table
> rather than re-derived by hand: the 2026-09-16 run deletes **0 of 4**
> and the following one deletes **4 of 4**. The pair clears at 03:00 on
> 2026-09-17. *(It did. Measured 2026-09-21 by Session 243: the oldest
> retained `sysadmin.service` row is ingested 2026-08-24 07:54:54 and the
> duplicate count is **0**. The marker is **removed rather than left** —
> after its moment a standing prediction reports `unknown` for ever, and a
> prediction that has been measured is no longer one. `SNAG-LOG-014` is
> closed.)*
>
> **Rule 7 is not engaged, which is the question this sitting was told to
> measure first.** The wall clock rule 9 requires in the prose is not a
> figure this module can test — `03:00` matches **none** of the six
> `CLAIM_PATTERNS` — so naming it adds no `unclaimed:` finding and creates
> no second producer of a fact some check reads. The instant stays the
> single licensed exception rule 9 already names: stated twice, in the
> marker and in the sentence, and *pinned* rather than trusted.
>
> **The first live member is exactly the case `SNAG-DOCS-008` closed, and
> by a route that entry did not predict.** It measured that 28 of the
> block's distinct wall clocks are stated more than once — 88 distinct at
> `305152a`, up from 86 — so an arbitrary instant already had a 6 % chance
> of being pinned by an unrelated sentence. The region stated `03:00`
> exactly **once** before this paragraph existed, and it was not a clock
> at all: it is the PCI bus address in `amdgpu 0000:03:00.0`, which no
> pattern over four digits and a colon can tell from a time. Driven both
> ways at the live region, with the
> marker on a sentence that omits the clock — the sentence-scoped pin
> returns `unknown` naming the remedy, and the pre-`SNAG-DOCS-008`
> region-wide pin finds the string and returns `match` with the prediction
> never having been written down anywhere. A five-character needle cannot
> tell a time from a device identifier, so the hazard was wider than a
> count of clocks could see.
>
> **And this block is its own regression test, which is why the count
> above is dated to a commit.** Writing it puts the needle into the region
> **five** more times — six in all, one of them a second copy of the bus
> address. Under the old rule that is exactly how a clock got written down
> for ever; under the new one it changes nothing, because exactly one of
> the six is the marker's own sentence and the other five sit in
> neighbouring ones. The sitting as a whole moves the collided set
> **28 → 31** and the distinct count **88 → 93**, and only part of that is
> this paragraph: correcting the daemon-start and alert claims below wrote
> six further wall clocks. The figures are attributed rather than given as
> one delta, because a paragraph that states a property of a region it
> goes on editing can be falsified by its own author an hour later — which
> is how the *once* above came to be wrong before it was caught. Session
> 170 recorded the same self-reference for a title; a needle five
> characters wide reaches it faster, and a paragraph measuring a region it
> is about to join has to say which region it measured.
>
> **A concurrent sitting found the half of this the tests could not, and
> the live marker is what let either of us see it.**
> `TestTheConventionAgainstTheRealDocument`'s prediction guard has stood
> since 2026-08-24 and its loop body **had never executed** — the family
> being empty, what it asserted for eleven days is that an empty `for`
> completes. Driven at the first live marker it is *half a guard*: it
> keys on two note substrings, and every `_convention` refusal writes a
> note carrying neither, so a naive instant (`SNAG-ESTATE-013`'s own
> founding shape), an unparseable one and a marker carrying **no**
> instant all passed. Verified here before acting rather than taken on
> trust — all three driven at the real document — and closed with a
> `kind` test, which is deliberately not a verdict test: a prediction
> whose moment has passed earns `unknown` by rule 8, so asserting the
> verdict would turn this red the morning a prediction came *true*, the
> calendar writing a failure. Found by the concurrent session
> `sysadmin-assistant-38`, which stood down on the documents rather than
> duplicate them and wrote nothing.
>
> **The same live member broke a Session 170 guard, and the break is the
> hazard read from the other end.**
> `TestThePinIsNarrowedToOneSentence._claim` took the *first* `expires`
> marker, which named the marker that test had planted only because the
> real block carried none — so the zone-fault drive silently began
> measuring this sitting's prediction instead of its own subject, and
> asserted `match` where it wanted `unknown`. Repaired by keying the
> selector on the marker's argument and **asserting it matches exactly
> one**, rather than by taking the last, which would restate the
> positional assumption the document has just falsified. `SNAG-LOG-004`'s
> ordering a fifth time: a change that widens what a reader can see is a
> regression surface for whatever reads it — here the reader was the test
> suite and the widening was a document edit.
>
> Seven mutations driven and seven killed, each on its intended test —
> four at the new class (marker deleted, offset dropped, marker moved off
> its sentence, a passed boundary reported as agreement) and three at the
> widened guard. Suite **3534 → 3538**, the baseline measured by stashing
> to `305152a` and re-collecting rather than read off the cell below,
> which is **216** stale; `ruff` and `mypy` clean; all ten ops claims
> green and all **21** snag entry checks holding beside the register's
> three meta-checks, with the register unmoved at 134
> entries and 23 open — this sitting closed nothing and corrected a date.

> **A membership claim is read from one sentence, because the region it
> was read from is append-only** (2026-09-04, Session 170).
> `SNAG-ESTATE-016` is **closed**. `check_open_titles` asked whether every
> unresolved title appeared *anywhere* in the printed region, and that
> region has grown to **178,301** characters of accumulated sittings — so
> a recurring fault's title satisfied the test on the strength of having
> been written down once, four sittings ago. `claim_sentence` narrows the
> haystack to the sentence bearing the `open_titles` marker: **290**
> characters at `9a3fe30`, and the two blocks then differ in exactly the
> one title.
>
> **Falsified against the real commit rather than against a fixture of its
> shape.** At `9a3fe30` the sentence named `GPU was reset — every client
> lost its VRAM`, which had resolved, and omitted
> `High VRAM usage on AMD Radeon RX 7900 XTX`, which was open; the missing
> title's **one** occurrence in the region sits more than **5,000**
> characters below the marker, in an account of a fault four sittings old.
> The narrowed check reports `3 named` against `4 open` there and names
> the missing row. **The same block still matches the four rows its own
> sentence describes**, which is the control that separates a check that
> discriminates from one that merely got louder — without it, any change
> making the check noisier would pass.
>
> **The marker became load-bearing and rule 7 survives it.** A marker may
> never gate a check; here it decides *where* to look rather than
> *whether*, since the population comes from the alert table and is read
> either way. So deleting it turns a `mismatch` into an `unknown` naming
> the remedy and **can never yield a `match`** — driven at one block in
> both spellings. Rule 2's tri-state is what lets a marker be
> load-bearing without being a switch. Two markers with one key are
> refused rather than resolved (`read_claim`'s rule), which is a live
> shape here: `migration_head` is marked in two places.
>
> **Two of the tests had to be repaired before they could kill anything,
> and the first is the one worth carrying.** A test asserting that a full
> stop inside a quoted title does not end the sentence stayed **green**
> when the lookahead it credits was removed — a quoted title is blanked
> by the code-span veil before any boundary is looked for, so it asserted
> a behaviour and named the wrong mechanism. Its real population is a
> **bold decimal in prose**, which the veil cannot reach, and the figure
> has to sit *between* the titles and the marker or the cut lands
> harmlessly ahead of the list. The second placed a parenthetical after
> the marked sentence, where the extraction stops at the marker's own full
> stop and the terminator class decides nothing.
>
> **The sentence terminator gained a trailing class on a measurement.**
> The first pattern demanded whitespace immediately after the stop and
> agrees with the final one on **both** real blocks, so nothing here would
> have caught it. The region carries **290** prose full stops with no
> space after them, overwhelmingly the bolded lead-in — the shape almost
> every paragraph in this block opens with — and without the class the
> terminator is refused and the marked sentence runs backwards through the
> whole lead-in. That is this entry's defect at one paragraph instead of
> at 178 kB.
>
> **This block is its own regression test.** Writing it puts a fourth copy
> of `High VRAM usage on AMD Radeon RX 7900 XTX` and a third of
> `GPU was reset — every client lost its VRAM` into the region, above the
> sentence that claims them — which under the old rule was exactly how a
> name got written down for ever, and under the new one changes nothing.
> Thirteen mutations driven and thirteen killed; suite **3504 → 3526**,
> `ruff` and `mypy` clean; the snag register moves 24 open to 23 and the
> closed entry carried no check, so nothing had to be re-homed.

> **A derived relation cannot be broken by a config edit, and the entry's
> own named fix was measurably inert** (2026-09-04, Session 169).
> `SNAG-CFG-006` is **closed**. `CriticalSignature.arrives_at` was
> *asserted* against the shipped `config.yaml` by a test, and
> `sysadmin/reload.py` installs a config no test has seen — so a `SIGHUP`
> narrowing the kernel source back to `error` disarmed the GPU-reset
> declaration with the suite green. `read_journal` now **derives** its
> ceiling from the declaration (`read_ceiling`) and admits a declared
> signature past the rung gate (`admits`), so the relation the test was
> guarding no longer exists to be broken.
>
> **The entry named one of the reader's two gates, and measuring it is
> what said so.** Driven against the live kernel journal with
> `severity_filter` at `error`, forcing `-p 6` returns the **same 32
> entries** and the **same zero** `VRAM is lost due to GPU reset!` lines
> — journalctl hands the line over and the Python filter, which
> `read_journal`'s own docstring calls the authority on what is stored,
> drops it one loop later. Both gates move now, and from **one argument**
> so they cannot drift apart. Live either side: at the narrowed config
> the reader goes **32 → 35** stored with **0 → 3** VRAM lines, and
> **1,788** undeclared info lines are still dropped — the narrowing still
> governs everything nobody has spoken for, which a wholesale floor drop
> would have destroyed.
>
> **Two of ten falsifications passed against deliberately broken code,
> and both were the wiring.** Handing `declared=None` at either call site
> left all 74 tests green, because every one of them passed `declared` to
> a reader itself — *"nothing drove `_record_start`"*, a fifth time. Two
> behavioural drives now go through the real `read_journal` and the real
> `_read_log_file` with a narrowed source and ask whether the declared
> line survived. A third first draft was caught by its own detector: the
> AST guard keyed on the **name** `SEVERITY_ORDER` and reported
> `core/escalation.py`, which owns a *different* constant — three alert
> rungs against five log severities — so it keys on **provenance**, the
> import from `sysadmin.monitor.journal`. **That guard then caught the
> sitting's own new snag check**, which compared two configured rungs by
> hand; it asks `admits` now, which is the gate's own question. Suite
> **3478 → 3504**, `ruff` and `mypy` clean; the 20 pre-existing snag
> checks unmoved either side by stash-diff.
>
> **Two entries opened, and the first's own draft claimed no remedy existed** —
> `SNAG-LOG-018`, the read budget a narrowed declaring source spends on
> lines it discards: **1.9 %** efficiency against the 40 % Session 62
> named as a defect, empty today because the shipped config reads
> `info`. Checking took a minute and found one: `journalctl --grep`
> filters *within* a priority selection and returns **3 lines of the
> 1,825**. It is refused on cost rather than absence — the key is the
> *normalised* signature, so the pattern would be a second
> implementation of `signature()` as a regex, and two reads fork the
> cursor `SNAG-AGENT-005` exists to keep single. **21 checks now**: the
> new entry carries one, driven at a *narrowed* copy of the shipped
> config because the shipped one cannot exhibit the residue. One of its
> three falsifications passed against broken code and found a defect in
> the check itself — the "no residue to observe" sentence went into the
> list the verdict was computed from.
>
> **The second entry came from a green check disagreeing with a
> hand-corrected block.** `SNAG-ESTATE-016`: `check_open_titles` matches
> a title as a substring of the *printed region*, which is **178,301
> characters** of accumulated history, so a name written down once
> satisfies it for ever. At `9a3fe30` the block's sentence named `GPU was
> reset — every client lost its VRAM` while the open row carried `High
> VRAM usage on AMD Radeon RX 7900 XTX`; the check reported `4 named, 4
> open`, `match`, because both strings appear somewhere in the region.
> The fall note the docstring delegates the other direction to fires on a
> **count**, and the count was right.

> **A published surface that was never published is gone** (2026-09-04,
> Session 168). `SNAG-DOCS-003` is **closed**. The five contract models
> describing estate-manager's 8400 routes survived a year of tidying
> only because `sysadmin_tray` ships in the wheel, so an import list is a
> published surface. Re-measured on the day rather than quoted from the
> sitting that refuted the blocker: **31** `sysadmin_service` wheels on
> this box, **0** carrying `sysadmin_tray/` code; no git remote and no
> upstream; and an AST sweep of **20,795** `.py` files outside the
> checkout finds **0** importers — keyed on the import and never on the
> name, because estate-manager defines all five names itself and a
> name-keyed sweep answers 5/5 and names the wrong party. Falsified with
> a planted importer beside a same-named local decoy, because a constant
> observation is not evidence until something would have forced a
> different one.
>
> **The removal moved a measurement nobody was aiming at.**
> `test_contract_reachability`'s docstring recorded that the walker, driven
> at the **pre-fix** registry, could judge only **12** of the 15
> unreachable models — three leaking in as roots from the shim's own
> annotations and from the shim tests. Both sources went with the fix, and
> the same drive at the same file now reports **15 of 15**. So the entry's
> stated reason for keeping `test_none_of_them_are_defined_in_contracts`
> expired on the commit that closed it; the test stays on what
> reachability still cannot do — refuse a name that comes back *with a
> reader wired to it*.
>
> **Four tests went where the entry said three, and two of the four would
> have passed.** `test_a_live_re_export_does_not_warn` and
> `test_an_unknown_name_still_raises_attribute_error` assert, after the
> removal, a Python language guarantee about a module with no
> `__getattr__` — a vacuous green reading as coverage of a mechanism that
> no longer exists. A second empty population arrived with it and is
> stated: `PortfolioAction` over `RecommendationInfo` was the registry's
> only subclassing pair, so rule 3's base-class edge now has no member in
> `contracts.py` and is exercised only by the synthetic. Suite
> **3485 → 3478**, `ruff` and `mypy` clean; commit cites estate message
> `e045373e`.

> **The daemon's 462 MB is mostly page cache, and the entry's cost was
> never in it** (2026-09-04, Session 167). `SNAG-SYSD-008` ranked
> **P3 → P4** and measured. `memory.stat` answers it in two lines:
> `anon 155 MB` against `file 298 MB`, with `inactive_file 298 MB` and
> `active_file 0` — the file half cold and reclaimable, so
> `memory.current` was never the daemon's demand. The process reads
> `VmRSS 178 MB`.
>
> **The first suspect is refuted and was costed against a row count 8×
> too high.** `GET /api/logs/trends` serves in **44–48 ms** with zero
> anon growth over five requests, because the `GROUP BY` runs in
> PostgreSQL. `log_entries` holds **84,265 rows**, not 627k — retention
> purged it — though the table is still 602 MB of dead-tuple bloat and
> `alerts` is 374 MB for **13 live tuples**, which is PostgreSQL's
> resident set and invisible to this cgroup.
>
> **The source is the file organiser.** `file_hash` reads the first 1 MB
> of every file ≥ 1 KB under the scan root for its duplicate
> fingerprint — **317,180 files**, of which the daemon faulted
> **5.07 GB from disk** in one 97-second scan. `journalctl` inherits the
> cgroup too, but its startup catch-up reported `truncated_sources []`.
>
> **Steady state costs nothing, and a driven scan prices the rest.**
> Across 23 idle minutes `read_bytes`, `memory.events max` and the
> pressure counter were all frozen. A manual scan pinned
> `memory.current` at **511.6–512.0 MB for 95 seconds**, took reclaim
> **17,331 → 34,804** and `memory.pressure full` **83,055 →
> 165,871 µs** — **82.8 ms of stall**, against 83 ms for the 2.4 hours
> before it.
>
> **There is no leak: peak does not track uptime.** A 4 min 33 s
> invocation peaked at **512M**; an 11 h 3 min one at **230.5M**;
> 9 h 55 m → 224.9M, 12 h 28 m → 226.5M. What does ratchet is the *anon*
> half — the scan took it 146.4 → **230.8 MB** and it fell back only to
> 203.2 MB — and that is the half that could OOM, at roughly **4×**
> today's file count.
>
> **It has never been killed, and the proposed rerank rested on a
> misread line.** Every stop in the unit's recorded history is
> `Deactivated successfully`, with `oom_kill 0`; systemd prints
> `Consumed … 512M memory peak` on every stop as routine accounting, so
> it is a postmortem statistic and not a kill notice.
>
> **Raising `MemoryMax` is refused on measurement**, which inverts the
> entry's own ranking of its two candidates: the box has **186 GB RAM,
> 166 GB available and zero memory pressure**, so the cap is 0.27 % of
> RAM and a bigger number buys a bigger throwaway cache. The fix that
> matches the cause is `posix_fadvise(POSIX_FADV_DONTNEED)` at the hash
> read. One residual is stated rather than explained: across
> **2026-08-28 → 08-31** every invocation peaked at 222–246 MB while the
> scan ran 14 times on 08-28 alone, and nothing here measures what
> separates those days from these.

> **One GPU reset now occupies one alert row** (2026-09-04, Session
> 166). `SNAG-LOG-015` is **closed**. A full-card amdgpu MODE1 reset
> writes eleven distinct signatures in six seconds and this family opened
> a row for each: live on 2026-09-04, ten `warning` rows at a single
> `created_at` instant, ten tray fingerprints, and the declared row that
> names the fault arriving beside ten fragments of its own wreckage.
> Driven against the real chain out of `log_entries`: **11 → 1**, with
> every swallowed signature named in `details['members']`.
>
> **The entry's hardest question dissolved rather than got answered.** It
> asks what resolves a swallowed member *"since each is a separate open
> row with its own dedup lifecycle"*. The fold runs over the `faults`
> dict **before** `_open_alerts`, so a swallowed member is never a row —
> nothing to resolve, and `monitor/collation.py`'s flip-flop needs two
> owners of one row where there is exactly one. `SNAG-AGENT-005` reached
> the same shape for the same reason: a log line cannot un-write itself,
> so this family's fixes are raise rules.
>
> **The relation is reused, not restated.** `log_actions.correlate` is
> `group_incidents`' machinery lifted out of it, with the first-sightings
> filter left behind at the advice caller where it belongs. It stays in
> `log_actions` deliberately: `check_check_interval_looks_away` measures
> `SNAG-SVC-001` by which modules the advice side imports, and rehoming
> it would let a later fix satisfy that entry while its check went on
> reporting *still holds*.
>
> **The window is a second constant, and the measurement is why.**
> `INCIDENT_WINDOW_SECONDS` is 5.0, derived where one incident spans
> 349 ms and two are 64.4 s apart. This population is not that one: all
> five resets in the journal span **4.9579–4.9675 s** from first error
> line to `VRAM is lost` — amdgpu's fixed timeout schedule, which is why
> they agree to ten milliseconds — and the nearest genuinely-two-incidents
> separation among 81,509 kernel error lines is **7.04 s**. So 5.0 clears
> by **32 ms, 0.6 % of its own value**, and the knife edge was driven:
> at 4.9674 s the real chain gives eleven rows, at 4.9676 s one.
> `ALERT_INCIDENT_WINDOW_SECONDS = 5.9` is the same derivation applied to
> this population, and a test pins it against the measurement because the
> failure mode is silent — a slower reset would quietly reopen the entry
> with nothing going red.
>
> **The fold may never quieten anything**, so a louder sibling is left
> standing rather than swallowed — which is what stops an operator's
> `known_noise` entry on the reset being overridden by a fragment.
> Opened `SNAG-LOG-017`: a chain astride a poll boundary folds only the
> half arriving with the declaration. Measured empty (5 of 5 resets
> landed in one poll), worst case is the pre-fix count, and both
> candidate fixes are worse than the 8 % they would buy.

> **The declaration was written from the wrong kernel, and the first real
> reset found it** (2026-09-04, Session 165). Session 164 shipped
> `CRITICAL_SIGNATURES` the night before; at 10:35:32 the next morning
> the dGPU took a full amdgpu MODE1 reset — `Illegal opcode in command
> stream` from a `vkd3d_queue` thread, the per-queue reset refused by
> firmware that does not implement it, `VRAM is lost due to GPU reset!`
> — and the monitor said nothing louder than `warning`, which is the
> defect Session 164 existed to remove.
>
> **The key carried a device prefix that had moved between kernel
> branches.** `6.18-lts` logs `amdgpu 0000:03:00.0: amdgpu: VRAM is
> lost…`; mainline dropped the redundant second `amdgpu:` by `7.2.2`,
> which the box was *already running* when the declaration was typed
> from the LTS journal. So the widened filter worked — the line reached
> `log_entries` for the first time in that table's life — and delivered
> it to a declaration that could not see it. Both halves shipped and one
> was inert, which is the multiplicative shape stated one block down,
> arriving inside its own fix.
>
> **The guard could not have caught it.** It read `DECLARED_KEY in
> CRITICAL_SIGNATURES` with `DECLARED_KEY = ("kernel",
> signature(VRAM_LOST))` — a value compared against itself, green on
> every kernel including one that has reworded the line. It meant
> *provenance* and asserted a *value*. Both spellings are declared now,
> sharing one value object because the title and reason are one fact,
> and `tests/test_critical_signature_live.py` is the discriminating
> half: it reads what this box actually stored and turns red on the
> first reset after a reword. Driven at the pre-fix state, the live test
> goes red where the old assertion still returns `True`.
>
> **Neither spelling is legacy.** `linux` and `linux-lts` are both
> installed and a `linux` upgrade invalidates `LoaderEntryDefault`, so
> the box can boot either without anybody choosing — the mechanism that
> put it on LTS on 2026-09-03.
>
> **The branch is not the fault, either.** The identical signature
> occurs on `7.1.9` mainline (2026-08-29, blaming `kwin_wayland`),
> `6.18.48-lts` (2026-09-03) and `7.2.2` (2026-09-04) — so the boot-default
> flip did not cause the resets, and the note saying it did is corrected.
> What 7.2.2 changed is diagnostics, not failure rate.
>
> Opened `SNAG-LOG-016` (a reword of the *payload* empties the live
> test's population and it skips). **A restart is owed** — the
> declaration takes effect at start.

> **The monitor could not say the GPU had been reset** (2026-09-03,
> Session 164). The dGPU took three full amdgpu MODE1 resets in 8.2
> hours — each one destroying every GPU client's VRAM on a 24 GB card
> shared by four services — and the loudest thing this service said was
> a `warning` log row. Two independent reasons, and fixing either alone
> is not half the benefit but none.
>
> **The event was below the reading threshold.** amdgpu stamps the
> diagnosis at `err` and the event at `info`: `GPU reset begin!`, `MODE1
> reset`, `VRAM is lost due to GPU reset!` and `device wedged, but
> recovered through reset` are all `PRIORITY=6`, and `severity_filter:
> error` becomes `journalctl -p 3`. Counted in `log_entries`: **0** rows
> for all four event lines, **4** apiece for the two symptoms. The
> wreckage was stored and the event was not.
>
> **And `critical` was unreachable regardless.** `chk_alert_severity`
> admits three rungs, journal `error` maps to alert `warning`, and
> amdgpu never uses `PRIORITY` 0–2 — so all **44** amdgpu alert rows on
> this box are `warning`.
>
> `CRITICAL_SIGNATURES` is the mirror that did not exist: `known_noise`
> and `COVERED_SIGNATURES` both move a rung *down*, nothing moved one
> up. A declared entry widens the gate **and** the rung. The first
> incident opens at `warning` and the second inside
> `critical_repeat_hours` escalates — `failures.py`'s two-failures rule
> applied to an event family, because one reset is survivable and three
> in eight hours is a different claim.
>
> Three opened: `SNAG-LOG-015` (one reset still occupies twelve rows),
> `SNAG-CFG-006` (a SIGHUP can disarm the declaration with the suite
> green), `SNAG-SYSD-008` (the daemon runs at 91.5 % of `MemoryMax` and
> its cgroup has forced reclaim 59,388 times). **A restart is owed** —
> the widened filter and the declaration both take effect at start.

> **The blocker was the part that was wrong** (2026-09-03, Session 163).
> `SNAG-DOCS-003` is **unblocked**, not closed. It says closing it needs
> *"an operational fact this repository cannot check"* — where the wheel
> went. It was checkable here in one sitting: **no git remote and no
> branch upstream**, so the repository has never been pushed; **not one
> of the 31** `sysadmin_service` wheels on this box contains
> `sysadmin_tray/` code, every one a uv *editable* stub of a `.pth` and
> dist-info, checked by `unzip` rather than by name; CI has no publish
> step; `syncthing@gaddi` runs but shares only `/srv/seedvault-backups`
> and `~/Documents/DMDocs/Self`, neither covering `~/projects`; and
> `~/projects/.backups/sysadmin_assistant.git` is a leaf whose only
> remote is a local path and whose newest ref predates the module by
> three weeks. The published surface the entry protects has never
> actually been published.
>
> **Zero importers box-wide, and the sweep keys on the import rather
> than the name.** Not one `from`/`import` statement reaching `sysadmin`
> or `sysadmin_tray` exists outside this checkout, across `~/projects`,
> `~/.claude`, `~/.local` and `~/.config`. The distinction decides the
> answer: **estate-manager defines all five names itself** in
> `service/estate_service/projects/contracts.py` off its own local
> `Contract` base, so a **name**-keyed sweep finds 5/5 over there and
> names them the importer, plausibly and wrongly. They went across with
> ADR-0005; nothing of theirs breaks.
>
> **The negative was falsified before it was believed.** A planted
> importer beside a decoy *local* class of the same name went through
> the same sweep — the importer reported, the decoy ignored, the plant
> removed by a shell trap. Without it, zero-because-clean reads exactly
> like zero-because-the-pattern-never-matched.
>
> **Announced as `e045373e`, before the commit that will carry the
> removal.** No filing was *owed* — a measured-empty audience files
> nothing. It was sent because estate-manager holds the only two
> surviving references and wrote them down itself: **ADR-0069** names
> this module inside its own rule-3 audience measurement, and
> `GET :8400/api/audit/readers` carries **two rows** for it, of 127 over
> 6 repositories. Neither breaks; both stop being true. Their inventory
> is **not** a second opinion on the audience — it keys on port and
> document authority, never on Python imports, and holds **zero** rows
> referencing 8500 from any repository.
>
> **One code edit is owed and was deliberately not made.**
> `check_deprecated_contracts`'s docstring still says the fact is one
> *"this repository cannot check"*. Its verdict is unaffected and still
> `match`, so it is a wrong sentence rather than a wrong answer, and it
> is recorded in the entry rather than fixed by a sitting scoped to
> answering the blocker. *(Discharged 2026-09-04 by deletion rather than
> by correction: the check retired with the entry, so the wrong sentence
> went with it and none was written to a function nothing calls.)* Docs only, no code touched: the live parser
> reads **124 entries / 19 open** either side, **9 of 9** ops claims
> `ok`, and no restart is owed.

> **A marked cut said an identity was lost; now it gives one back**
> (2026-09-03, Session 162). `SNAG-LOG-013` is **closed**. A cut
> signature carries `signature_digest` of the **whole** signature — the
> eight characters `alert_title` has stamped since Session 122 — so the
> roll-up's member lines, the incident title and the three
> single-signature titles all come apart. Open entries **20 → 19**;
> nothing opened.
>
> **The obstacle was refuted by the entry's own alert half.** It argues
> a divergence-aware cap *"needs the sibling set and so cannot live in a
> per-row pure function"*. True of that remedy — and the digest is
> per-row and pure, so `capped_signature` was simply where it had not
> been applied. The entry's *"two candidate fixes, neither cheap"* is now
> false in both limbs: the producer fix landed for a different entry and
> emptied the population without touching the class, and the second was
> never the only per-row option, only the only divergence-aware one.
>
> **Four rules, three of them the opposite of the obvious
> implementation.** The digest is **imported, never restated** — a local
> `sha256(...)[:8]` gives the identical value, so all five
> value-asserting tests pass against the copy and only an AST walk
> catches it. It digests the **whole** signature and never the cut,
> because the colliding pair's cuts are one string and a digest of what
> survives would render as a discriminator and separate nothing. It is
> **appended past the bound**, deliberately the opposite of
> `alert_title`, which subtracts because `TITLE_MAX` is a column — so
> the cut point does not move and no existing member line lost a
> character. And **only a cut carries one**, asked of `truncate_at_word`
> rather than re-derived from the constant.
>
> **The weekly review takes the cut without the stamp, and the
> population deciding that is not empty.** `log_review._quoted_signature`
> gates on `figure_free` because its render reaches a *model* under a
> prompt that carries no digit from the data by construction. Measured:
> **8 of 79** retained signatures are cut and **8 of 8** are figure-free,
> so gating on the *rendered* line — the tidier-looking shape — would
> have deleted every cut signature from the prompt rather than
> un-stamping it. Live, **two** such lines reach the real prompt today
> and its data half carries **zero** digits.
>
> **`figure_free`'s stated exception is unreachable**, measured on the
> way past. Its docstring said `_HEX` leaves `0xN`, *"digit-free in
> intent and not in fact"*; `signature()` runs `_NUM` **after** `_HEX`,
> over its result, so the `0` is eaten and `0x1f` arrives as `NxN`.
> **79 of 79** live signatures pass the gate. The gate stays — its input
> is only *typed* as a signature — and the docstring is corrected.
>
> **A measurement bug nearly mis-ranked the fix, and it was in the
> reader.** The first sweep read `log_entries` with a `psql -F`
> separator and dropped every row whose `message` carries a newline —
> which is every core dump and every traceback, the exact class this
> entry is about — reporting **3** cut signatures against the true
> **8**. `row_to_json` puts each row on one line.
>
> **Six mutations, each red on the right test**, and the last is the one
> worth carrying: a second digest of its own lands red on the AST walk
> **alone**. The check retired with the entry and the detector did not —
> `TestACutSignatureCarriesItsDiscriminator`, `FROZEN_TABLES`' rule for
> the eighth time here, carrying `probe_signatures`' derive-the-prefix-
> from-the-constant argument so a future `SIGNATURE_DETAIL_CHARS = 400`
> cannot read as a fix in the one remedy the entry rules out. Suite
> **3430 → 3430**, and the total holding still is a coincidence rather
> than a green: counted per file by stashing to HEAD, **9 added**
> (`test_log_actions` 57 → 65, `test_log_review` 35 → 36) against **9
> retired with the check** (`test_snag_claims` 384 → 375). `ruff` and
> `mypy` clean, **19 of 19** snag verdicts and the register's four
> conventions unmoved either side, **9 of 9** ops claims `ok`.

> **The class was still producible and the entry's own obstacle was
> refuted** (2026-09-03, Session 161). `SNAG-LOG-013` declares
> **`owed`** — the last of twenty open entries to declare a disposition,
> so the register reads `owed 1, blocked 4, decided 10, delegated 5` and
> every open entry now says whether a sitting is owed work on it.
>
> **The producer changed and nobody had looked.** The entry blames
> `SNAG-LOG-008`'s JSON envelopes and that class is gone; driving the
> real `signature()` over all 80,380 retained rows, **8 of the 79**
> distinct signatures are cut today against the **2 of 50** the entry
> last recorded, and **4 of the 8 are stack traces** — one Python
> traceback and three core dumps. `systemd-coredump` spends **70–73
> characters** on `Process N (X) of user N dumped core. Stack trace of
> thread N:` before the first frame, and a frame renders `#N NxN
> <symbol> (<object> + NxN)` at 29–46 characters, so the 120-character
> cap admits **one and a half frames** and falls inside frame 2 of all
> three live dumps. Two `abort()`-path crashes of one binary are
> identical to the cap by construction. A stack trace is
> boilerplate-first, which is the exact **opposite** of the envelope
> class that was fixed.
>
> **The live margin is 43 characters and it is luck.** No pair on the box
> shares a capped prefix; the closest is two `mosquitto.service` dumps
> agreeing over **77** of 120, and the survivor survives only because its
> frame 1 carries a symbol (`sub__clean_session`) where the other carries
> `n/a`. An empty population is not a closure — this document's rule,
> stated for this entry twice already.
>
> **The residue is prose alone, which no bullet said and the check cannot
> see.** Driven at a colliding pair through the real `recommend()` with
> the **real** `alert_title` — the check stubs it with a fixed string —
> the roll-up's structured members already come apart:
> `members[].alert_title` reads `… (truncated) [a028de53]` against
> `[d9aa53f0]` and `members[].signature` carries all 247 characters. So
> Session 122's discriminator reaches this surface's machine-readable
> half for free, and what still collides is the rendered `detail` member
> lines and the row `title`.
>
> **Which is why the disposition is `owed` and not `decided`.** The entry
> says a divergence-aware cap *"needs the sibling set and so cannot live
> in a per-row pure function"* — true of that remedy, and its own alert
> half already shipped one that is per-row and pure. `capped_signature`
> is simply where the digest has not been applied. Nothing was fixed this
> sitting and nothing was refuted: all **20** snag verdicts and the
> register's four conventions are unmoved, and the ops block's
> unresolved-alert claim was corrected 2 → 3 (`Unusual RAM usage` opened
> after Session 160 wrote it).
>
> **And a docstring stopped being true while nothing about it moved.**
> Estate message `b96a337c` announces their ADR-0102: a `wiring`
> finding's `fingerprint` becomes `wiring:<hook>:<code>:<event>`, so the
> limit `judge_audit_wiring` filed — *two events declared by one hook
> would share one fingerprint and therefore one `standing_days`* — is
> **closed at the producer**. Corrected there, and in
> `judge_audit_findings` rule 4, whose incidental claim that `code` is
> the fingerprint's last `:`-separated segment is now true of twelve
> checks and false of one.
>
> **Verified in their tree rather than taken, and the wire cannot show
> it.** `wiring` has filed **zero** findings in 938 across 262 runs, and
> live `GET /api/audit/findings` served three, every one three-part
> (`ports` ×2, `docs` ×1). So the correction reads their source:
> `Finding.fingerprint` appends `aspect`, `checks/wiring.py` is its only
> setter, and `as_payload` publishes no `aspect` key — **committed,
> which is not deployed on 8400**. `detail['event']` and `subject` are
> unchanged, so rule 1's identity and rule 2's discriminator are
> untouched.
>
> **Both repositories had recorded a two-option choice and both options
> were wrong**, which is what the round trip bought. Their entry framed
> it as *admit `detail` to the identity* or *forbid a hook declaring two
> events*; the second cannot close it, because `hook_wired_undeclared`
> iterates `~/.claude/settings.json`, whose cardinality is the owner's,
> and both codes share one subject.
>
> **The pin is pre-staged and was falsified against their real
> dataclass**, because a pin over an empty population is green whatever
> it asserts. Driving `Finding.as_payload` here: the shipped shape
> passes, a rolled-back `aspect=None` goes red, an `aspect` disagreeing
> with `detail['event']` goes red, and the whole-file finding gaining
> one goes red on the colon count. Suite **3429 → 3430**, `ruff` and
> `mypy` clean, 24 register verdicts and 9 ops claims `ok`. The daemon
> was restarted for a docstring — the deploy check compares mtimes, and
> paying it beats leaving a `no` a reader learns to skip.

> **The two families' disjointness was a handover, and git says so**
> (2026-09-03, Session 160). `SNAG-SVC-002` is **decided**, not closed.
> The entry says `timer_stale` and `stalls.py` do not overlap here and
> calls that "a property of this box rather than of the design". The
> enumeration nobody had done: **10** services are declared `kind:
> timer`, and none intersects `AGENT_NAMES` (6) or `agent_schedules` (5)
> by service name, by unit stem, **or by what its `ExecStart` actually
> runs** — the third key being the one a name comparison cannot reach.
> Live at the same moment `stalls.py` watched 5 agents with 0 stalled and
> `GET /api/services/actions` served 5 rows with the `timer_stale`
> population still **zero**. The two families have named **zero** common
> subjects on this box.
>
> **But the scenario the entry calls hypothetical already happened.**
> Commit `5cc04cc` (2026-08-08) installed `sysadmin-organiser.timer`,
> declared it `kind: timer`, and set `agents.project_organiser.enabled:
> false` in the same sitting — for the *same subject* the daemon was
> scheduling as an agent. Its message states the rule: *"Monitoring the
> timer **replaces** the self-monitor's stall watch over that agent."*
> So the disjointness is a **handover**, performed deliberately on the
> one subject that could ever have been both, and `estate-manager-scan.timer`
> runs that agent's work today under ADR-0005. What is fragile is what
> *carried* it: `summarise_agent` gates on `schedule.enabled`, so one
> config flag was the whole separation — the fragility
> `agent_schedules`' own docstring already names.
>
> **`sysadmin/monitor/handover.py` makes the handover a fact the daemon
> checks.** An `agent:` key on a `kind: timer` entry, three rungs:
> `breached` (the agent is scheduled **and** enabled — the job runs
> twice, both families speak), `flag_carried` (the `5cc04cc` state,
> silent and one edit away), `unknown_agents`. A link naming a
> **retired** agent is silent, which is the key's purpose —
> `AGENT_NAMES` and `agent_schedules` answer different questions and both
> are read. **Reported, never refused** (`config_keys` rule 1): a boot
> refused over a coherence finding is `SNAG-DB-005`'s twenty-three hours
> bought for a job that runs twice. `handover_walked` keeps
> zero-because-blind apart from zero-because-clean.
>
> **The cross-reference the entry recommends has a cost it does not
> price**: `sysadmin-organiser-timer` and `project_organiser` share no
> string, so feeding `stalls.py` a timer-backed population needs the same
> declared link — a schema key, not a wiring change — and once the key
> exists the cheaper thing to spend it on is a config-time report rather
> than the alert-time machinery the entry itself calls "the second owner
> arriving with more machinery".
>
> **It does not close the entry and the check correctly says so.** The
> guard imports neither family, so all three instruments are unmoved:
> both still speak on the synthetic subject, `timer_stale` still owns no
> ladder, the importer sets are still disjoint. What moved is that the
> state in which they speak about a *real* subject is now detected before
> it is served. Driven live: `POST /api/sysadmin/reload` reports
> `handover_breached: []` with `handover_walked: true`, and against the
> same file with the link re-pointed reports the breach; a **restart** in
> that state writes `handover_agent_still_scheduled` at `WARNING` —
> stored, counted, raising nothing, which is the right rung for a
> tidiness finding. The loud path was driven by restarting into the bad
> state, because a clean report proves nothing about it.
>
> **The residue is `SNAG-SVC-005`**, filed with the twenty-second check:
> the key is a declaration, so an agent moved to a timer with no key is
> invisible. Both closures were priced and refused — deriving the link
> needs a subprocess in a parse path and *recognises an application*
> where the key **honours a statement**, and making the key mandatory
> puts `agent: null` on nine of ten entries as ceremony. Its check
> answers the same entry three times (as shipped, re-pointed, key
> removed) because the obvious observation is a constant.

> **A constraint value nothing wrote had a referent, and dating seven
> rows is what found it** (2026-09-03, Session 159b). `SNAG-DB-006` is
> **fixed**. `chk_run_status` has admitted `cancelled` since migration
> 001; the entry named two *opposite* fixes — drop the value, or find the
> path that fills it — and left the choice open because nothing recorded
> which was intended. The seven live `running` rows decide it. Every one
> is followed by a **clean** daemon death within **0.032–61.2 s**, and for
> every one the next `agent_run_completed` for that agent comes from a
> **different PID**. The mechanism is `scheduler.shutdown(wait=False)` in
> `main.py`, read rather than inferred: the first row was inserted **19 ms
> before** `scheduler_shutdown` in the journal.
>
> **The control is what makes that evidence.** Of 40,383 `completed` runs
> **162 (0.401 %)** started that close to a death, and the separation is
> total — no run starting more than 61 s from a death has ever got stuck.
> `file_organiser` is the sharpest line at **0 of 112** completed against
> **3 of 3** stuck, the widest exposure of any agent at ~108 s a scan.
> Conditioning cuts the right way: a run killed at shutdown *cannot* be
> `completed`, so the depressed base rate is the argument rather than a
> bias against it. Live rate **4.9 %** of daemon deaths (7 of 144).
>
> **The shape that won is a third one the entry does not name.** A
> shutdown-path write is what anyone reaches for and it **races the thing
> it describes** — `shutdown(wait=False)` returns while the worker thread
> is still in `_execute`, and three of the seven had 30–60 s of scan left
> — so `sysadmin/core/abandoned_runs.py` sweeps at **startup**, which is
> `unit_failure.py`'s argument one table over. Its reach into SIGKILL and
> power-off is stated as **theoretical**: all ten crash deaths in the
> journal died 2.1–4.8 s in, before the scheduler could fire anything, so
> on the live population both shapes reach 7 of 7 and the race is the
> only discriminator that is not hypothetical.
>
> **Forward-only by refusal, never by a constant.** The seven predate the
> stamp, so the sweep cannot attribute them and **counts** them —
> `ports_checked`'s rule — where an age cutoff would have been an invented
> constant expressing a fact the row already carries. The id is minted
> in-process rather than read from systemd's `INVOCATION_ID`, because this
> service reads no environment variables and a lone exception is a
> convention that has stopped being one.
>
> **Verified live, twice, because the path had never run here.** Restart 1
> reported `abandoned_runs_unattributable count=7` with no closures;
> `POST /api/files/scan` was then killed 2 s in and restart 2 reported
> `abandoned_runs_closed count=1 agents=['file_organiser']`, writing **the
> first `cancelled` row in this database's life**. The seven are still at
> seven.
>
> **Three of thirteen falsifications passed against deliberately broken
> code.** Deleting the `IS NOT NULL` conjunct changed nothing — `NULL <>
> 'x'` is `NULL`, so rule 3's refusal was carried by three-valued logic
> rather than by the clause written for it; the clause stays and is pinned
> by compiling the statement, since no behavioural test can see it go.
> `status == CANCELLED_STATUS` compared the constant to itself. And
> **nothing drove `_record_start`**, so deleting the stamp passed all
> twenty tests. The check retired with the entry after reporting
> `refuted` correctly, and its detector is re-homed as
> `tests/test_abandoned_runs.py`, `FROZEN_TABLES`' rule a fifth time.

> **The register declared dispositions and nothing read one back**
> (2026-09-03, Session 159). `convention:next-action` is the guard
> Session 157 pre-staged: it resolves every `SNAG-` id in `HANDOFF.md`'s
> published next action against the register **as it is now**, and
> refuses one whose entry declares `decided` or `delegated`. The failure
> is measured, not imagined — Session 138 refused `SNAG-TRAY-011`'s
> proposed remedy on 2026-08-30, Session 156 stopped one bullet short of
> the refusal and published that remedy as this repository's next action,
> and `roadmap.py` republished it to the estate board verbatim.
>
> **Every id, and the two narrower rules were refuted rather than
> rejected.** Driven over the **21** distinct next actions in
> `HANDOFF.md`'s history: reading every id fires **once**, on Session
> 156's line, with **zero** other refusals. *First id* is refuted by the
> live line, whose first id is `SNAG-SYSD-003` cited as evidence rather
> than named as the work. *Ids before the first em-dash* catches the same
> single true positive — the house form is `Verb SNAG-ID — reason` — and
> is blind on **2 of 21** whose only id sits after one, which is a guard
> whose failure direction is silence.
>
> **It reads the entry's value now, and a list would have been wrong
> about it within the hour.** At `4d8a464`, the commit that took the
> disposition population from zero to seventeen, `SNAG-SYSD-003` declared
> `Open — decided`; at `3f5af0d` an hour later it closed and its `Status`
> line went with it. One line, one id, two registers, **opposite
> verdicts** — driven both ways as a test. A **closed** entry is reported
> and never refused, at the owner's ruling: nothing separates an id cited
> as evidence from one named as the work, and **12 of 21** historic lines
> name an entry that is closed today.
>
> **Two consumers, one implementation**, which is what makes the owner's
> "both" one owner rather than two. `check_next_action` reports at
> preflight and postflight, where a refusal is news to judge;
> `tests/test_handoff_shape.py` calls *that function* rather than
> restating the rule and refuses the commit. Ten mutations driven, each
> red on the tests about its own rule, and two are worth carrying: the
> first-id reader leaves the em-dash test green (correctly — its specimen
> has no id before the dash, which is what isolates the two rules), and
> ignoring `is_open` cannot reach the now-versus-snapshot test, because
> that test's closed stand-in drops its `Status` line faithfully to
> `SNAG-SYSD-003`.
>
> **The pin skips on the tree, never on the import.** `next_action_line`
> reads this document rather than importing their
> `next_action_from_handoff`, because `estate_service` is on this path by
> an editable `.pth` that is in **no lockfile** — so the pin is a test,
> and `pytest.importorskip` would have disarmed it on the one box where
> it matters the moment a `uv sync` pruned that install. It skips only
> when estate-manager is absent from the box entirely; present-and-
> unimportable is a **red**. The two reads are byte-identical today.

> **A `decided` entry closed by measuring the question it reserved**
> (2026-09-02, Session 158). `SNAG-SYSD-003` is **fixed**:
> `sysadmin.service` ordered `After=… ollama.service` for a runtime
> retired on 2026-07-24, and the entry reserved *"whether this service
> should order against `alfred-inference.service` at all"* as the
> question to settle first. It is not a question about preference. That
> unit is a **user** unit at `~/.config/systemd/user/` and reads
> `LoadState=not-found` in the **system** manager, where
> `sysadmin.service` lives — a system unit cannot order against a user
> unit, so the named successor would have rebuilt this entry's own defect
> under a newer name. One name removed, nothing put in its place.
>
> **The check retired and the detector did not**, `FROZEN_TABLES`' rule a
> fourth time — and the guard is **wider than the entry** on purpose.
> `tests/test_unit_ordering_live.py` asserts that *every* unit named in
> `After=` resolves, because the entry's stated cost was never the one
> name but that the unit file is read as the record and whoever derives a
> unit from it copies the staleness forward. `RETIRED_UNIT` outlived its
> check by taking a **second job**: a sweep asserting every ordered unit
> resolves cannot tell health from a `systemctl` that says `loaded` to
> everything, so `ollama.service` is now that guard's negative control and
> must come back `not-found`. Five mutations driven, each red on the tests
> about its own rule — including the reader answering `loaded` to
> everything, which turns the control red **alone** while the sweep stays
> green, and naming `alfred-inference.service`, which is the successor
> ruling demonstrated rather than asserted.
>
> **The box is one `sudo` behind the checkout and it is said rather than
> left to be found**: `/etc/systemd/system/sysadmin.service` was
> byte-identical to the repo copy before this edit and still carries the
> old line. The install is
> `sudo cp systemd/sysadmin.service /etc/systemd/system/ && sudo systemctl daemon-reload`,
> which this session could not run (`sudo -n` wants a password here), and
> **no restart is implied** — `After=` decides ordering at start and
> nothing else, so the running daemon is unaffected either way.
> `systemd-analyze verify` is clean on the edited file.

> **The register measured whether each entry still holds and nothing
> measured whether work was owed** (2026-09-02, Session 157). The next
> action this sitting was handed named `SNAG-TRAY-011`, whose remedy
> Session 138 had measured and refused on 2026-08-30 at `7be7643`, 25
> commits back — and the refusal has sat in the entry's own **Decided**
> bullet ever since. Session 156 read the bullet above it, *"Shape of a
> fix as originally proposed"*, and stopped one short of the
> `— refuted 2026-08-30, see the decision below` that closes its heading.
> The refused remedy then went out estate-wide:
> `GET :8400/api/projects/sysadmin_assistant` was serving it at
> `findings.roadmap.next_action` when this sitting looked.
>
> **Re-measured rather than taken from the entry**, three days and 48,325
> records on: **725,892** journal records over **22.52 days**, every one
> `PRIORITY=6`, and **zero** at `WARNING` or above across the unit's whole
> recorded life. Both of Session 138's gates are unmoved. The entry stays
> open and its check still reports `ok`, which is a deliberate non-fix
> working exactly as designed.
>
> **So the gap was never that entry's.** Classified across all twenty open
> entries, four of them read in full rather than off their bullet
> lead-ins: **3 owed**, **4 blocked**, **5 delegated**, **8 decided**. A
> ranker picking off the open count alone had a **15 %** chance of landing
> on work. `priority` cannot answer it and neither can a check — a check
> answers *does this still hold*.
>
> **The obvious marker was already refused by an entry in this document.**
> `SNAG-ESTATE-012` rejected a marker whose *"absence is
> indistinguishable from forgetting it — the thing it is meant to
> detect"*. What ships is not a different spelling but a **sweep**:
> `convention:disposition` reports absence over the whole open population
> in every state, so forgetting is a number rather than a silence.
> It read **20 of 20 open entries declare no disposition** on the day it
> shipped; Session 158 annotated the seventeen entries owed nothing and
> it now reads **3 of 19**, `blocked 4, decided 7, delegated 5`. The
> three that remain are exactly the three measured `owed` —
> `SNAG-LOG-013`, `SNAG-SVC-002` and `SNAG-DB-006` — so the undeclared
> set and the work queue are the same set, which is what the sweep was
> for. The nineteenth is `SNAG-SYSD-003`, closed the same afternoon: a
> `decided` disposition records a decision that can be re-opened, not a
> closure, and this one was re-opened by the owner within the hour.
>
> **The field is Alfred's, not a new one** — 60 of them there, none here,
> and `estate.snags` has parsed it since it moved to the library. **The
> hazard is their parser**: its completion vocabulary contains
> `won't fix`, the natural English for the `decided` disposition, so such
> a value would close the entry in the reader that publishes this
> estate's movement figures. Every value is anchored with `Open — ` and
> the check proves it per value by calling their **public**
> `status_is_done` rather than restating their word list. Announced
> before the commit at a measured audience — message
> `70377694-c7e6-4cb8-9c92-7c9c3258f82b`.

> **A red now says which of two things happened, and the observation had
> to move inside the call to say it** (2026-09-02, Session 156).
> `SNAG-TEST-003` is **fixed**, and it was the last open entry naming no
> check: **0 of 20**, down from 1 — by the entry closing, not by a check
> being written, which is the only way that figure may fall for an entry
> whose claim is an assertion's wording. A check would have to reproduce
> an intermittent fault on demand.
>
> **The separator is a precondition, not a differential.**
> `test_notify_send_does_not_return_on_a_bus_with_nothing_listening` said
> a red meant the D-Bus activation *"is gone from this box"*, so any red
> read as good news and the honest response to good news is to relax the
> guard. It now asserts that `plasma_waitforname` was started under this
> fixture's own bus **before** it asserts the call blocked. Three states,
> measured rather than reasoned about: hazard intact — activated, blocked,
> **8.03 s**; reading disturbed by three kills, which is `SNAG-TEST-004`'s
> own mechanism replayed — **activated**, returned at **3.06 s** with
> `exited with status 255`; hazard genuinely gone on a bus whose config
> declares no service directory — **not** activated, returned at
> **0.03 s** with `ServiceUnknown`. `returned` is common to both failing
> readings; the activation is what tells them apart.
>
> **Sampling during the call is forced rather than a refinement.** The
> disturbed row's waiter is dead by the time the call returns, because
> killing it is what errored the call — so one check afterwards reports
> "no activation" for a disturbed box and a fixed one alike, which is the
> collapse being removed, one line later. `_notify_send` is a `Popen`
> polled at 20 ms, an interval derived from a measured 48–50 ms activation
> latency against a waiter that then persists for the whole block. Its
> failure direction is the unsafe one and is stated in the assertion
> itself. The budget was **not** raised, which the entry named as the
> thing that must not happen.
>
> **What outlives the finding is the ordering.**
> `TestTheRedSaysWhichReadingItIs` pins that the two asserts read
> `outcome.activated` then `outcome.returned` — swap them and the block
> assertion's message asserts a waiter was started on a box nobody looked
> at. It reads each assert's `test` and never its `msg`, because both
> messages quote the same fields and a whole-node walk would report
> agreement whatever the order was. Both mutations land red. And
> `SNAG-TEST-004`'s scoping property was re-measured under the new probe
> rather than assumed to survive it: two offset concurrent runs, **4 for 4
> green** at the full 8.7 s, zero stray waiters.

> **The fold's second fact was published rather than derived, and the
> difference is whether a consumer restates a judgement** (2026-09-02,
> Session 155). `SNAG-SVC-004` is **fixed**.
> `_folded_row` rule 5 wrote *whose* step is leading into the folded
> `detail`; `health_review._service_facts` projects `title` and
> `action` and not `detail`, so the weekly review printed one finding's
> remedy under another finding's title with nothing saying the subject
> had changed. `ServiceRecommendationInfo.action_from` is that fact as
> its own field. Open entries with no check: **1 of 21**, down from 2 —
> by the entry closing, not by a check being written.
>
> **The entry's own last bullet decided where the guard goes.** A check
> asserting the *fix* cannot serve a registry whose `ok` means *"the bug
> is still real"*, so the drive is `TestTheStepsProvenanceIsProjected`
> rather than a twenty-first check — `FROZEN_TABLES`' rule met from the
> other end, and `SNAG-SVC-003`'s own closure one sitting earlier.
>
> **`stands_for`'s treatment is a derivation, and copying it literally
> would have been the defect.** That field is
> `m.title for m in members if m.kind != r.kind` — a restatement of what
> *swallowed* means, which is structural. The same shape here is
> `next(m.kind for m in members if m.kind in STEP_SUPERSEDES)`, which
> restates which member **won**: a judgement `_folded_row` already took,
> free to drift the day that tuple widens. `SNAG-DB-003`'s shape, and
> `judge_queue_invariants`' *"the mask is read, never recomputed"*. So
> the producer publishes it. One of the seven mutations is exactly that
> recomputing projection and exactly one test is red on it.
>
> **Both fold shapes were live at the moment of the fix**, which is the
> discrimination a specimen of one could not have supplied.
> `alfred-career-mail-timer` (`outage` + `timer_failed`) reads
> `action_from: "timer_failed"`; `venture-chat` (`outage` + `flapping`)
> reads `""`, because `flapping` promotes nothing. The digest line the
> entry quoted as *reading correctly by luck of one string* now says so
> in its own words.
>
> **Empty is deliberately not `ports_checked`'s not-knowing.** The field
> is `""` both for a row whose step is its own and for a producer that
> does not publish it; every other absent-vs-present collapse here hides
> a *blind* reading, and this one cannot, because both spellings mean
> "render nothing extra". Spelling it as the row's own `kind` was
> refused — it fires the renderer's clause on every folded row and makes
> every consumer compare two fields to learn nothing.
>
> **The refused fix is pinned rather than merely avoided**, and the
> audience for a published surface was measured. Projecting `detail`
> would carry the provenance *and* every swallowed row's own body into
> the review's blob, so a test asserts `detail` is absent from the
> projection. Outside this repository the route is named in one place —
> estate-manager's parser corpus copy of `snag_list.md`, a fixture and
> not a reader — and `estate-map.md` records one consumed route from
> 8500. A measured-empty audience files nothing.

> **The instrument was also the safety catch, and the check that needed
> two witnesses is the one whose subject is an action** (2026-09-02,
> Session 154). `SNAG-AGENT-013` has the **twentieth** check. Every
> other drive in this registry writes something and rolls it back; this
> one enters `_handle_status`'s auto-restart branch, whose whole point
> is that it starts a unit on this box — in a module a shell script runs
> at both ends of every sitting. So `restart_unit` is **patched rather
> than reached**, and the probe's unit is minted per call, because a
> swap that silently failed to bind could then only aim `systemctl` at a
> unit that does not exist. Open entries with no check: **2 of 22**,
> down from 3.
>
> **The patched call is the harness's witness and `_failure_counts` is
> the subject's.** They can disagree only if the branch reaches systemd
> by a name the drive no longer patches — a blind instrument, not a fix.
> Without the second witness an instrument that stopped binding would
> have reported this entry fixed *and* let the restart through, so the
> two are read side by side and a disagreement is `unknown`.
>
> **The obvious instrument would have shipped green.**
> `self._arbitration` *is* consulted a dozen lines below the branch, so
> a source walk finding it in `_handle_status` reports it consulted; and
> a walk asserting it is absent *above* the branch refutes the moment
> somebody moves a line. What the entry claims is about the **order of
> two conditions**, and only running the branch can say which won.
>
> **Three arms, and the control holds a lease rather than holding
> none.** `unread` is the premise — four conditions guard that branch
> and three of them are the harness's — while `other` and `stopped`
> differ in exactly one boolean, which is what separates a gate on the
> *unit* from a gate on *"a lease is granted"*. The second would stop
> restarting `alfred-backend` because the estate stopped `venture-chat`.
> Driven: moving the premise to a granted arm reddens exactly the
> lease-gate test and nothing else.
>
> **The population is reported and never scored**, which is rule 1 in
> the direction this entry makes easy to invert — the leaf being set
> *raises* the entry, so wiring the count to the verdict could only
> retire it at the moment it became live. Live: all three arms
> restarted, **0 of 31** services set `auto_restart` with a controllable
> unit, and `venture-chat.service` is the one unit this daemon has
> recorded the arbiter stopping, across **4** rows. The two halves have
> not met and the distance between this box and the defect is one leaf.
>
> **Two things only driving it could have said.** Thirteen mutations
> were driven and all thirteen land red on their intended test — one of
> them removed the swap altogether, letting the real `restart_unit` run
> and `systemctl --user restart` fail harmlessly against the minted
> unit, which *demonstrated* the second guard rather than arguing for
> it; and re-recording the call while still delegating to the real one
> is the only mutation that lands on the sentinel assertion, which is
> what makes it evidence rather than decoration. **mypy chose the
> stand-in's parameter name**, rejecting `target` against
> `restart_unit(unit, user)`: a stand-in that is not substitutable for
> the name it replaces is a control the next caller breaks.
>
> **`rung_sql` became `schema_sql` and moved beside `query_one`.** The
> fault it prevents — no `search_path`, so an unqualified name resolves
> to `public` and fails as *"the database did not answer"* — is a
> property of that connection, not of the entry that first hit it, so
> the second caller borrows the rule rather than copying the fix.

> **The entry named its own trigger and had no instrument for it, and
> the instrument found the entry understating its own residue**
> (2026-09-02, Session 156). `SNAG-AGENT-012` has the **nineteenth**
> check. Its last bullet reads *"what would raise it is the first
> `alert_rung_left_stale` line that is not a test's"* — a mechanical
> trigger nothing could answer. It is a query now, and *"that is not a
> test's"* needs no clause: `log_entries.source` holds the **unit**, and
> a test runs in the sitting's own process and never under
> `sysadmin.service`. Live: **0** trigger rows against **135**
> `alert_raised` rows that witness the path works, and **0** open
> `% unreachable` rows. Open entries with no check: **3 of 22**, down
> from 4.
>
> **The obvious instrument would have shipped green and inert.**
> `may_quieten_in_place('critical', 'info')` is `False` and is the root
> of the whole mechanism — and it is exactly what `step_for`'s
> resolve-and-re-raise deliberately leaves alone, since that fix exists
> *because* an in-place escalation is inaudible. A check asserting the
> predicate answers `match` either side of the fix, which is
> `check_review_schedule_unread`'s defect. It is carried as a **premise**
> in the detail; the verdict is driven, entering at `_raise_judged`
> rather than at `_refresh_open` because the fix may land in either.
>
> **The drive says something sharper than the entry does.**
> `SNAG-AGENT-009` made a held row's *sentence* correctable, so what a
> poll leaves behind is not a stale row but an internally inconsistent
> one: `message` reading *"the unit did not come back when the lease
> released"* at `severity: info`. A check reading `_refresh_open`'s
> boolean would have reported the row brought up to date.
>
> **Two things only running it could have said.** The first draft's four
> statements were **unqualified**, so `query_one` — which opens a
> connection with no `search_path` — resolved `log_entries` to `public`
> and every one answered `ProgrammingError`, reported as *"the database
> did not answer"*: a sentence about an unreachable database over a
> wrong statement, green verdict, silent population. And **one of
> fourteen mutations passed against every test in the class**: a drive
> aimed at `_refresh_open`, one level below the fork, where the author
> supplies the `raised = 0` by hand because they put the standing row
> there. `_suppressed` is the third-party witness inside the subject —
> `_raise_judged` writes it and `_refresh_open` never does.
>
> **`_refreshed` was briefly in that premise and the fix stand-in is
> what removed it.** That counter is incremented *inside*
> `_refresh_open`, so `step_for`'s shape — which replaces that method —
> leaves it at zero with the hold plainly fired, and the check reported
> `unknown` over a landed fix. A control the fix breaks, caught by the
> one stand-in written to model the fix rather than the defect.
>
> **A pre-existing red was found and repaired, and it was a box-wide
> selector again.** `tests/test_quietened_judgement_live.py` asserted
> `result.details["resolved"] == 0` — the **whole run's** sweep — while
> meaning "no resolve-and-re-raise under this drive's own title". The
> judge's two live dev-server breaches (3110, 8110) made it 2, so the
> test was red on any box with an editor open and green otherwise:
> `SNAG-TEST-004`'s class one file over, and seasonal. Verified
> pre-existing at HEAD by stashing before blaming this sitting's work.
> The scoped count still turns red under a modelled resolve-and-re-raise.
>
> **The folded row led with a step that cannot work, and the thing that
> proved it was the timer nobody was looking at** (2026-09-02, Session
> 151). `SNAG-SVC-003` is **fixed**. `_folded_row` took `action` from
> the anchor, so `alfred-career-mail-timer` led with
> *"POST /api/sysadmin/services/alfred-career-mail-timer/restart"* — a
> remedy that re-arms a schedule that was never the problem, while the
> step reaching the failing job sat three lines below it in the row it
> had swallowed. `STEP_SUPERSEDES` names the kinds whose step reaches a
> unit the anchor's cannot, and today that is `timer_failed` alone,
> because its step operates on the **triggered** service.
>
> **Rule 4's refusal stands and only one field moved.** Cause-first
> anchoring was put to the owner in Session 149 and refused; the title,
> the points, the rung, the grade and the evidence are still the
> anchor's. Live either side: `alfred-career-mail-timer` leads with
> `journalctl --user -u alfred-career-mail.service -n 100`,
> `venture-chat` is unmoved, and the endpoint holds **6 rows and 83
> points** both before and after.
>
> **The entry's discriminator was one it did not name.** It scopes the
> defect to "a timer fault", which points at repairing the outage row
> whenever the subject is a timer. Two timers carried an outage row that
> morning — `alfred-career-mail-timer`, folded, and
> `pgbackrest-backup-timer`, whose job had started succeeding the day
> before and which therefore produced no `timer_failed` row at all.
> **Both got the identical restart step and only the folded one's was
> wrong**, because for an armed timer whose *unit* went inactive the
> restart is right. So the condition that refutes the step is exactly
> the condition that folds, and the subject-keyed implementation is a
> driven mutation that only `pgbackrest-backup-timer` lands red.
>
> **The promotion would have dropped the anchor's step**, which is
> `_folded_row` rule 4 facing the other way: the tray and
> `health_review` render `title`, `detail` and `action`, and `members`
> is none of the three. The superseded step is named in the `detail`
> with the finding the leading step belongs to. The step itself was
> **run** and reaches a SQLAlchemy insert error in Alfred's ingest at
> 08:20:25 — that repository's to fix, and already its SNAG-50.
>
> **One of the nine tests was written twice and the first could not have
> failed**: it drove a lone `timer_failed` row, which no implementation
> can get wrong, since `recommend` never folds a group of one. Nine
> mutations, each red on the right test; 19 snag checks unmoved by
> stash. `SNAG-SVC-004` is the filed residue — the provenance line lives
> in `detail`, and the weekly review projects every field but that one.

> **One fault occupies one row now, and the entry that asked for it had
> measured half of its own population** (2026-09-02, Session 149).
> `SNAG-SYSD-006` is **fixed**: `group_faults` and `_folded_row` in
> `service_recommendations.py` fold a service's `EVENT_ARGUED` findings
> into one row that **names** every finding it swallows —
> `log_actions.group_incidents`' treatment, applied at a relation that
> has no clock and no systemd graph in it. Live either side,
> `GET /api/services/actions` went **8 rows → 6** and
> `alfred-career-mail-timer` occupies one row carrying both its
> findings.
>
> **`total_recoverable_points` is 78 before and 78 after**, which is the
> invariant that decided the arithmetic rather than a happy result: an
> anchor keeping only its own share would have taken the same box's
> total to **53** on the day the list got easier to read.
>
> **The entry scoped the defect to timers, and running the endpoint
> found a second instance it never named.** `venture-chat` has served
> `outage` at 26 points beside `flapping` at 25 since the endpoint
> shipped on 2026-08-25 — eight days, one service named twice, no timer
> in it anywhere.
>
> **Two controls belonging to a *different* open entry decided the
> design.** `SNAG-SVC-001`'s check finds its row by a **top-level** scan
> for `kind == "check_interval"` and its subject produces exactly
> `flapping` + `check_interval`, so the obvious "one row per service"
> would have reported a live entry refuted; its third limb reads this
> module's **import set**, so reaching for `group_incidents` by
> importing it would have refuted the same entry from the other side.
> Driven by stash before and after: all 18 snag checks unmoved.
>
> **The fix had to land twice.** `health_review._service_facts` projects
> the anchor's `title` and `action` into the weekly review, so the first
> version named one finding and never said the other existed — the
> roll-up that cannot name anything, one consumer downstream of the fold
> that promised not to. `SNAG-SVC-003` was the filed residue — the
> folded row leading with the anchor's step, and for a timer fault the
> swallowed step being the better one — and it was **closed the same day
> by Session 151**, one field wide.

> **A `kind: timer` check read the wrong unit for its whole life, and
> two silent failures were standing behind it** (2026-09-01, Session
> 147). `SNAG-SYSD-005` is fixed and deployed. The check asserted the
> **timer** was armed and recorded the **timer's** `Result` under the
> name `last_result` — a timer's `Result` reports whether the timer unit
> started, so it read `success` on **10** of
> 10 declared timers while one of the ten jobs had failed on twelve
> consecutive mornings. It now resolves the started unit from systemd's
> own `Unit=` property and reads that unit's `Result`.
>
> **It was found by reading another repository's snag, and it found a
> second fault nobody had filed.** Alfred's SNAG-50 reports
> `alfred-career-mail.service` failing every morning for 20 days with
> *"nothing surfaces this"* — the unit is declared in this repository's
> `services.yaml` and this check wrote **3,988 unbroken `ok` rows**
> across the window. *(Alfred re-measured on 2026-09-04 and corrected
> that figure to **five** failures on 21 mornings, estate message
> `8c6da00e`: their reproduction counted traceback lines, not runs. The
> intermittency makes this finding stronger — a job failing every
> morning is noticed eventually; one failing five mornings in
> twenty-one is what a monitor is for, and this check said `ok` on all
> five.)* The first live run under the fix raised two
> criticals, not one: `pgbackrest-backup.service`, which
> `services.yaml`'s own comment calls *the only database backup on the
> box*, has failed **28** times and
> succeeded **zero** times since 2026-08-02, under 4,697 `ok` rows.
>
> **The half-state is what made it invisible from every other angle.**
> `pg_stat_archiver` reads `archived_count=5356, failed_count=0` with the
> last push minutes ago — **WAL archiving works**. So the repository grew,
> nothing errored anywhere, and nothing could expire, because
> `repo1-retention-full=4` is applied *during a backup*. Disk at 85 %.
>
> ***Two claims this entry made were overstated and the successful run
> refuted both — recorded here rather than quietly edited.*** It said
> *zero base backups* and *nothing to restore onto*. The run printed
> `last backup label = 20260307-141905F`: the repository held a **full
> backup from 2026-03-07**, taken **by hand at 14:19:05** — three minutes
> before the timer was enabled and three and a half before the broken
> unit was written. So recovery was possible throughout, to a
> **178-day-old** base plus ~5,356 WAL segments of replay: slow and
> fragile, not impossible. The error was inferring an empty repository
> from 28 unit failures without being able to read `/var/lib/pgbackrest`,
> which needs root — a population measured from the *caller's* failures
> rather than from the store, which is `ports_checked`'s rule turned
> around and pointed at this repository. Corrected at estate-manager as
> message `cc5f26e7`. *The `pgbackrest.conf` placeholder comment was also
> read as a second defect and is cosmetic — 5,356 archive-pushes prove
> pgbackrest parses that file.*
>
> **One authoring error, three instances, two files** — a directive split
> across two lines with no trailing backslash, found by
> `systemd-analyze verify` rather than by reading. `ExecStart=` loses
> `backup` (hence `[030] no command found`); `Description=` loses
> `Alfred`; and in the **timer**, `OnCalendar=*-*-*` loses `02:00:00`, so
> systemd resolved it to `*-*-* 00:00:00` and the backup that was written
> to run off-peak at 02:00 — `IOSchedulingClass=idle`, `Nice=10` — has
> been firing at **midnight** all along.
>
> **Neither fault is this repository's to fix** — the monitor does not
> own what it monitors, the units need `sudo`, and both were spoken and
> filed: estate messages `e5d17a89` (Alfred, the career-mail record),
> `aacd7e33` (estate-manager, the backup, routed there because
> `pg1-path` is the whole cluster and the stanza is merely *named*
> `alfred`) and `cc5f26e7` (the correction above).
>
> **`SNAG-SYSD-006` is confirmed and stays open** (2026-09-02, Session
> 148). The entry opened as a *prediction* — that once a failed job's
> `critical` checks accumulated past a rounding boundary, one fault would
> produce two advice rows — and named the re-read that would settle it.
> It did: `GET /api/services/actions` now serves `alfred-career-mail-timer`
> **twice**, an `outage` row at 5 recoverable points beside a
> `timer_failed` row at 0, off 101 `critical` checks standing unbroken
> since the first poll under the fix. `pgbackrest-backup-timer` serves
> one row and the survivor is the `outage` one, which is the entry's
> argument for refusing the cheap fix demonstrated rather than asserted.
> The remedy is `group_incidents`' treatment — a roll-up that names what
> it swallows — and that is a `KIND_ORDER` design question, not a patch.
>
> **The backup half is resolved.** The owner applied
> `scripts/fix-systemd-continuations.py` to both units at 22:19 and
> reloaded at 22:29; the run took **16.4 s**, `Result=success`,
> `ExecMainStatus=0`, wrote `20260307-141905F_20260901-222905I` and ran
> `expire` for the first time since March. `next_elapse` is now **02:00**
> rather than midnight. The career-mail half is Alfred's and stands
> open.
>
> **`SNAG-AGENT-011` is closed, and it closed on the limb that needed a
> night rather than on the commit** (2026-09-01, Session 146). The
> nightly `venture-chat unreachable` row opened at **00:01:16** at
> `info` — not `critical` — resolved at **05:51:19**, and carries
> `details['arbitration']` naming the lease, the profile and
> `stopped_by_estate: true`. The box was not stale: the daemon has served
> the fix since 2026-08-31 09:36:14, which is **8m36s before** the commit
> that carried it, because this repository restarts to verify and commits
> afterwards.
>
> **The check's headline could not close it, which is the conjunction
> working.** `sysadmin-check-snags` returns on limb 2 — a reader of
> `stopped_units` now exists — before any limb-1 branch can run, so limb
> 1's verdict was taken by neutralising the outer gate, and it refutes by
> the right one of three branches: *a quietening rather than a
> suppression*. The three readings the check said it could not separate
> were separated by hand and all three refuted — `mute_services` is
> empty, three post-deploy rows each carry a real granted lease, and
> `stopped_by_estate` is true on every one. So the population did not go
> quiet; only the rung moved.
>
> **The check retired with the entry and the detector did not**, for the
> sixth time. `TestTheDeployedQuieteningLive` reads the live `alerts`
> table and is stronger than the limb it replaces: limb 1 rebuilt a
> window from another project's timer, which moved on 2026-08-25, while
> these read the blob the fix writes. Its anti-vacuity pin is the
> load-bearing half — driven at a pre-fix world the two behavioural
> tests **skip**, so without the pin a box that never deployed the fix
> reads green. The register is now **18 of 22 open entries checked**, and
> `SNAG-AGENT-012` and `SNAG-AGENT-013` were deliberately not built:
> both were filed with measured-zero populations precisely so that this
> closure would not spawn them.
>
> **No restart is owed**: nothing the daemon imports reaches
> `snag_claims.py`, and the deploy check compares mtimes and cannot tell.
>
> **The reviews park now, and the number the owner settled is a deadline
> rather than a duration — which is what makes it work** (2026-08-31,
> Session 142). `SNAG-SCHED-003` and `SNAG-SCHED-001` both **closed**.
> The three weekly reviews take a GPU lease from the estate's arbiter
> through `estate.queue` and wait for the grant; `sysadmin/core/gpu_lease.py`
> is the module, `LLMClient.generate` gained `gpu_lease_held`, and no slot
> moved. Both checks retired with their entries; the guard did not.
>
> **One deadline, three budgets derived from it.**
> `schedules.review_lease_margin_minutes` (5) puts the deadline at
> `briefing_hour` less the margin, and each review subtracts its own
> dispatch instant: **3300, 2400 and 600 s** from 05:00, 05:15 and 05:45.
> Three independent leaves were refused because they say the wrong thing
> about the mechanism — `Arbiter.tick` returns early while **any** lease
> is granted and `_oldest_waiter` orders by `requested_at` across every
> profile, so the three are not waiting three lengths, they are waiting
> for **one instant** from three starting points.
>
> **estate-manager's close note corrected the arithmetic and the
> correction does not bite.** `_drop_overdue_waiters()` runs **first** in
> every tick, before the grant, so copying their `REVIEW_WAIT_SECONDS` of
> 1800 drops the 05:00 job at 05:30 — fifteen minutes early — and the
> 05:15 job by 22–72 s, which is the nasty one because it fails by a
> fluke-sized margin. Every deadline-derived budget ends at 05:55, past
> the whole recorded release band of 05:45:15 → 05:47:18. Verified in
> their source rather than taken from their message.
>
> **The blocker was not in the handoff and it belonged to another
> repository.** `POST /api/queue/acquire` answers `404` for a profile not
> in their `service/profiles.yaml`. Filed as message **`dcae132c`** with
> the cost and the FIFO consequence stated **before** the commit; they
> landed `sysadmin-review` (`stop: []` / `start: []`) the same sitting.
> The code shipped pre-staged behind a test gated on the profile
> appearing, so the sitting was never parked.
>
> **The checks were briefly wrong in the direction this family is named
> for.** Both read source, and source cannot see a `404`: the moment
> `gpu_lease.py` existed they reported `mismatch` over a Monday that
> still cost three narratives — `SNAG-SCHED-002`'s false retirement one
> sitting later and by the opposite route, the *remedy* promoted before
> it worked rather than the symptom promoted to the remedy.
> `_review_profile_published` made the arbitration limb a conjunction
> with the arbiter's own roster, every way of not-knowing returning
> `None` rather than `False`, and both went back to `match` until the
> profile landed an hour later.
>
> **Driven live, and the drive caught the fix working at a moment nobody
> arranged.** Lease 39, `wait 3300s, hold 600s`; the arbiter logged
> `lease 39 waits: GPU floor 26% over threshold 25%` and **parked it** —
> the whole entry in one line, because the old gate raised `GpuBusy` at
> that same 26 % and served a digest. `wait_deadline` came back at
> request plus exactly the derived 3300 s. Writing that drive also found
> a defect reading the code had not: `estate.queue.acquire` defaults
> `base_url` to its own `127.0.0.1:8400` and this module passed none, a
> second spelling of the estate's address in a process that already
> reaches it through `agents.estate_judge.base_url`.
>
> **Two follow-ons in the same sitting.** `ideas.md`'s GPU-gate-split
> entry is **dead by premise rather than by arithmetic** — the waiterless
> callers no longer reach the gate, so the window's population is zero
> and no recalculation revives it; marked rather than deleted, because it
> records estate message `df4113cb` being declined. And `HANDOFF.md`
> gained a **`## Scheduled action`** section, so a dated measurement stops
> occupying the one line the estate board publishes. Its two shape rules
> come from estate-manager's `roadmap.py`, and the second was driven as a
> counterfactual and fires: a `- [ ]` there, with `## Next action`
> renamed, made their parser publish the 2026-09-07 reading as this
> repository's next action. Guarded by `tests/test_handoff_shape.py`;
> announced as message **`8e693e05`** before the commit.
>
> **Two findings after the work, recorded rather than fixed.**
> `SNAG-AGENT-011` (**P2**, and the only unchecked open entry): the
> estate's arbiter stops `venture-chat.service` under a lease and this
> repository announces it `critical` — the one rung the tray leaves on
> screen — standing **~5h45m nightly**, the drain's hold to the second.
> The discriminator is `active_lease.stopped_units`, live on a surface
> `sysadmin/estate/client.py` already reads. Re-measuring before filing
> is what made it accurate: the obvious figure is **181 rows all-time**
> and **161 fall on 2026-08-11 → 08-14**, before the estate's queue owned
> the swap, so the entry carries the current regime's **20 of 23**. And
> commit `30bfbea` shipped `claude-preflight.sh` **without its execute
> bit** — a falsification's Python-written backup `mv`'d back over it —
> so the one script every sitting starts with answered `permission
> denied` while the suite, ruff and the pre-commit hook stayed green,
> because a mode is not content. Both fixed or filed; a sweep over
> `scripts/*.sh` guards the second.
>
> **Still owed: one reading, on 2026-09-07** — `llm_used` on the three
> review tables and the four grants and their order in the estate's
> journal. Prediction: **true, true, true**, health granted first at
> ~05:46 and disk last, behind estate-review.
>
> ---
>
> **The prediction came true and the mechanism came with it — and the
> ranking in the entry's own headline did not survive the morning**
> (2026-08-31, Session 141). `SNAG-SCHED-003` predicted **false, false,
> false** for the three `llm_used` values this box writes on the first
> Monday since the drain moved to 00:00. All three are `false`:
> `health_reviews` 05:00:03.92, `log_reviews` 05:15:00.06,
> `disk_reviews` 05:45:00.43. **No code changed this sitting.**
>
> **A false is not by itself a confirmation, which is the entry's own
> quieter half.** Nothing on those three surfaces separates *skipped for
> contention* from *llama-server was down*, so the stored flag is the
> prediction and the journal is the mechanism: each row is preceded by
> `llm_gpu_busy` from `sysadmin.core.llm_client` carrying `busy_percent`
> **99, 97 and 98** against `threshold: 25`, and followed within
> milliseconds by its own `*_llm_unavailable_used_fallback`.
> `alfred-inference.service` was `active` throughout — the alternative
> cause is refuted rather than assumed away — and
> `venture-enrich-nightly.service` finished **05:46:11**, a sixth
> consecutive night inside the recorded band.
>
> **The estate paid the identical fault the same morning and kept its
> narrative.** It took lease 38, polled **16 m 21 s**, was granted at
> **05:46:20** — nine seconds after the drain released — and generated in
> about a second. Same card, same drain, same hour: it waited and got its
> narrative while this repository read the card once at each of three
> slots and served three digests into the 06:00 briefing. The two nights
> the entry cites for them are 08-17 and 08-24, *before* they changed;
> this is the first night the two designs have been seen side by side
> under one holder. **The lease fix is licensed outright.**
>
> **The refutation is of our own headline, and the error is the
> instrument.** That headline says *two of the three* reviews are worse
> off, ranking disk least affected at **5 of 12, 42.5 %** over ±300 s.
> `ensure_gpu_idle` reads at the **dispatch instant**, 05:45:00.43 —
> **71 seconds** before the release — so disk lost too. A ±300 s mean
> straddles the release and reports as half-clear a slot that was fully
> occupied when it was actually sampled. The priority does not move: it
> was argued from three narratives, never from which is worst.
>
> **The check reproduces the refuted ranking and its verdict is still
> right.** Driven after the observation it reads `disk_review 6/14 busy`
> and names `generating into a held card: health_review, log_review` — by
> the same majority rule that produced the 5 of 12. The conjunction holds
> through health and log, so the entry stays green for the right reason;
> what is wrong is the sentence beside the verdict. Left as measured,
> because moving the sample to the dispatch instant changes the check's
> witness and belongs with the fix.
>
> ---
>
> **The measurement named the wrong contender, and the box had already
> recorded the right one** — `SNAG-SCHED-001` owed one number before its
> two fixes could be ranked. Taking it re-ranked the entry instead.
> Three findings, each from this box rather than from the estate's prose:
>
> **This repository gates, and its own check could not see it.**
> `sysadmin/core/llm_client.py:134` calls `ensure_gpu_idle(...)` from
> `estate.gpu` at a threshold of **25** — one pre-dispatch read, then a
> digest. The entry's AST walk searched `estate_queue`, `wait_for_dgpu`
> and two literals, found none, and the sentence it supported read
> *"neither party is gating"*. The walk was right about its four names;
> the generalisation was not. Filed and fixed as `SNAG-SCHED-002`, and
> **the obvious repair is the harmful one**: promoting `ensure_gpu_idle`
> to the refuting set retires `SNAG-SCHED-001` on the strength of a gate
> that predates it by eighteen days and fixes nothing. The vocabulary is
> split by what a gate *does* — arbitrating gates refute, deferring ones
> are reported as evidence and never can.
>
> **The occupant at 05:45 is `venture-enrich-nightly`, not the estate.**
> This box's own journal: the drain finished **05:47:18, 05:45:15,
> 05:46:58, 05:45:22 and 05:45:26** on 08-26 → 08-30 — *the same five
> values the estate published as its granted band*, so their band is the
> drain's finish and their review is granted after it. Every one is
> after our 05:45:00 dispatch. `resource_snapshots` corroborate in two
> signals at once: **99 %** busy at 05:44:45 on 08-30, and
> `vram_used_mb` **19,870 → 11,112** across the release.
>
> **A generation takes under six seconds, so the two never overlap.**
> The real prompt dispatched raw gives **80.0 tok/s** solo and **62.4**
> with two in flight — a **22 %** per-stream cost, both completing,
> nothing failing against a 120 s timeout. Session 79's fifteen-minute
> spacing was over-provisioned by two orders of magnitude and was never
> the scarce thing. The drain's **5 h 45 m** is.
>
> **Which makes the chain the entry, not the slot** — `SNAG-SCHED-003`,
> filed P2. Since the drain moved to 00:00, health **12 of 12** samples
> busy and log **12 of 12**, against disk's **5 of 12**: the two reviews
> the entry does not mention sit squarely inside an occupancy no
> schedule leaf reaches, and only a lease reaches all three. The estate
> meets the identical fault and **waits** up to 1800 s for its
> narrative where we defer and lose ours — which is the ranking
> inverted, since the entry priced the lease as the expensive option.
> Unobserved so far: no Monday has run in the new regime, **2026-08-31
> is the first**, and the prediction is false, false, false.
>
> ---
>
> **The gauge moved and the threshold deliberately did not** — estate
> message `d1939cf7` is **acted on and closed**. estate-manager's
> weekly review now *takes* a GPU lease instead of sampling a counter
> (their ADR-0076/0077), so it queues behind `venture-enrich-nightly`
> every Monday 05:30 and waits **915–1038 s** across the five nights
> they measured. This repository judges `oldest_waiting_seconds > 900`
> and says *"Either a holder never released, or the arbiter's tick loop
> has stopped granting"* — so the first alert would have arrived on a
> Monday morning, said the queue was starved, and been **wrong**.
> `judge_queue_invariants` now reads
> `oldest_unexplained_wait_seconds`, the same number with that third
> cause masked out by the producer. **900 is unchanged.**
>
> **Raising the threshold was the obvious fix and buys nothing.** At a
> bigger number the gauge still cannot separate a normal Monday from a
> stuck queue, it only says so later — and the Monday wait is bounded by
> *another repository's* timer, so any number clearing it is one
> schedule change from being wrong again. `config.yaml` carries that
> refusal beside the leaf now, because the leaf is where a future Monday
> false alarm sends someone.
>
> **Three rules, two of them the opposite of the obvious
> implementation.** The mask is **read, never recomputed** —
> reconstructing it from `waiting_reason` would be a second
> implementation of the producer's derivation, `SNAG-DB-003`'s shape, so
> a test drives an *inconsistent* payload and asserts the field wins.
> **Absent is not masked** — `payload.get(...)` answers `None` both for a
> producer that explained the wait and for one that does not publish the
> field, and collapsing them retires this family in silence the day the
> estate rolls back, so a payload without the key falls back to the old
> gauge and labels the row `wait_gauge: "total"`. And **the reason is
> named because the producer names it**: the two values that can still
> reach a row are exactly the disjunction's two limbs, which is what
> makes the existing sentence true again.
>
> **The trade is stated: a survivable absence is a silent one.** The
> fallback means the new field vanishing is invisible to every
> fixture-driven test, so the only place it can be loud is the live half
> — `test_the_wait_discriminator_is_still_published`. The three states
> are pinned against payloads built by running the estate's own
> `Arbiter.submit` → `tick` → `invariants` in their venv against a
> **scratch** database, never the live `estate` one, which estate rule 1
> forbids writing. The 2026-08-16 fixture is kept unmodified as the
> **legacy-producer** specimen, and a test fails if anyone hand-edits it
> into the new shape.
>
> **One snag opened beside the work: `SNAG-SCHED-001`.** Reading *why*
> the estate's review now takes a lease showed that it displaces **where
> it generates** from 05:30 to the grant — 05:45:15–05:47:18 on their
> five measured nights, which is this repository's disk-review slot at
> **05:45**. Neither party gates: an AST walk over `sysadmin/` finds
> **zero** bindings of `wait-for-dgpu`, `/api/queue/lease` or
> `estate_queue`, and the estate's lease arbitrates it against
> `venture-enrich-nightly` rather than against us. The entry claims less
> than it could — nobody has measured what two concurrent generations
> cost, so what is claimed is that Session 79's fifteen-minute spacing is
> now **false and unmeasured**, with the one deciding measurement named.
> Its check is a conjunction, because either of the two fixes must refute
> it or it is a control that survives its own remedy.
>
> **It ships untriggered**, which is why it was driven rather than
> reasoned about: `alerts` holds **0** `Estate queue…` rows all-time, so
> nothing standing needed reconciling and no fixture could have told us
> so. Ten mutations of the predicate and eight of the fixture and live
> guards were each driven and each lands red on the test that owns the
> rule. **+23 tests, 3125 → 3148**, suite green, `ruff` and `mypy`
> clean. **No ADR** — the last estate message got one because it carried
> `needs_ruling=true` and asked a question; this one is
> recommendation-only and the reasoning lives in the docstring beside
> the predicate.
>
> *Previously —* **The measurement refuted the remedy rather than sizing it, and the
> entry stays open as a deliberate non-fix.** `SNAG-TRAY-011` asked
> whether `sysadmin-tray` should gain a
> `log: {type: journalctl, severity_filter: warning}` block so
> `SNAG-CFG-005`'s config-key warning becomes an alert row. **It should
> not.** The block is inert at **two independent gates**, and the sitting
> that was told to measure volume found the mechanism instead.
>
> **Gate one is the priority stamp — `SNAG-AGENT-008`'s priority half,
> one program over.** `sysadmin-tray.service` has written **677,567**
> journal records over **19.49 days** (2026-08-11 → 2026-08-30), and
> **every one is `PRIORITY=6`**. `main()` calls
> `basicConfig(format="… %(levelname)-8s …")` — a text formatter emitting
> no `<N>` prefix — so systemd stamps captured stdout `6` whatever the
> level inside says, and `SyslogLevelPrefix=yes` on the unit strips a
> prefix nothing writes. `max_priority_for("warning")` is **4**, so the
> declared source reads `journalctl -p 4` and ingests **nothing, ever**.
> `journalctl --user -u sysadmin-tray -p warning` over the unit's whole
> recorded life returns **no entries**.
>
> **Gate two is the alert family, and it fails even if gate one is
> fixed.** `FAULT_SEVERITIES = ("error", "critical")`, and the ingest
> loop `continue`s on anything else — so a `warning` line is **stored and
> raises nothing**. A working prefix moves the line from `info` to
> `warning`, and both sit below the family's floor. The entry reached
> neither gate because it reasoned from the tray's *Python* level rather
> than from the journal's stamp and the consumer's floor.
>
> **The prerequisite is refused by the rule that established the
> prefix.** Reusing `JournalLevelPrefixFormatter` is legal — the tray
> already imports from `sysadmin.core` and the boundary forbids only the
> reverse — but that class extends `JsonFormatter` deliberately: Session
> 61 rule 2 holds that only the JSON formatter guarantees one line per
> record, since under a text formatter a traceback's first line is
> stamped `ERROR` and its body left `info`, *"worse than the uniform 6
> because it looks fixed"*. Making the tray's levels reach the journal
> means moving a GUI program to JSON logging.
>
> **The only reachable branch pays the whole cost and buys none of the
> benefit.** `severity_filter: info` is not inert — it ingests
> everything: **34,762 rows a day**, ~**1.04 M** at 30-day retention, for
> a source with **zero** `WARNING`/`ERROR`/`CRITICAL` lines in its entire
> recorded life. And it still raises nothing, by gate two. So
> `SNAG-LOG-004`'s warning bounds the one branch that is not already
> inert, which is the reverse of how the entry weighed it.
>
> **Nothing was fixed and nothing was closed.** Both of the check's
> channels are unmoved, `check_tray_report_unheard` still reports
> `match`, and its P3 is now confirmed rather than inherited. No code
> changed this sitting.
>
> *Previously —* **The section neither program watched has a watcher, and the two
> defects worth carrying were found by running it rather than reading
> it.** `SNAG-CFG-005` is **closed**. `sysadmin_tray/config.py` reports
> the keys under `config.yaml`'s `tray:` that its own allowlist does not
> read — one set difference against `TRAY_SECTION_KEYS`, warned and never
> refused. It ships **untriggered**: the shipped `tray:` carries six keys
> and every one is read, verified by restarting the real tray.
>
> **The obvious fix shape would have shipped green.** A walk of `tray:`
> against `TrayConfig`, the way `core/config_keys.py` walks `config.yaml`
> against `AppConfig` — legal, since the import boundary only forbids the
> reverse — and wrong: `TrayConfig` declares **19** fields and the section
> supplies **7**, the other twelve arriving from `notifications.tray:`,
> `api:` and `services.yaml`. A model walk calls `tray.reminder_hours: 5`
> declared when setting it there does nothing. The model over-declares
> relative to the section; the allowlist does not.
>
> **Two defects the entry did not know about.** `tray: 5` **crashed the
> tray** — `key in 5` raised `TypeError` out of the one section this
> module hand-parses, unhandled, while `_read_services` next door costs
> "a mute list, not a launch"; it is `unwalkable` now. And
> `tray.api_url` has **never** been read while the loader docstring
> promised it since `81b3bfb`, the module's first commit — the
> `if "api_url" not in kwargs` guard beneath was dead by construction and
> its comment is what the docstring copied. Both went, because a reader
> checking the new report against the old docstring concludes the
> *report* is broken.
>
> **A convention copied without the formatter that makes it work.** The
> first version wrote `logger.warning("tray_config_unknown_keys",
> extra={"keys": …})` — the backend's idiom, readable only because
> `JsonFormatter` folds `extra` in. The tray's formatter is
> `basicConfig(format="… %(message)s")`, so the live journal line was the
> bare event name, announcing that a key was dropped and unable to say
> which: this entry's own defect one level down. Caught by driving it
> through the real formatter, not by reading it.
>
> **`SNAG-TRAY-011` is the residue, filed rather than absorbed**: the
> warning reaches `journalctl --user -u sysadmin-tray` and nothing else —
> `composed_log_sources` returns **15** units and `sysadmin-tray.service`
> is not among them — and fires once, at startup, where the backend
> re-reports on every `POST /api/sysadmin/reload`. **3109 → 3125**, +21
> and 5 retired. Seven mutations driven, each red on the test about its
> own rule; an eighth landed red **by accident** and exposed a rule with
> no guard, and two of the new check's own tests were false greens — one
> aimed its stand-in past the decision, the other patched a function the
> check no longer calls.
>
> *Previously —* **The entry's headline fix does not boot, and one walk of the shipped
> file said so before a line of it was written.** `SNAG-CFG-004` is
> **closed**. It asked whether `sysadmin/core/config.py`'s 37 models
> should set `extra="forbid"` as `sysadmin/monitor/services.py`'s four
> do. Walking `config.yaml` against `AppConfig`'s field tree finds **ten
> keys the backend does not declare** — the top-level `tray:` section and
> nine leaves under `notifications.tray:`, every one read by
> `sysadmin_tray/config.py`, which parses the same file for itself. So
> the forbid is not a trade-off to weigh against `SNAG-DB-005`; it is a
> daemon that will not start on this box **today**, and a test builds the
> strict subclass and asserts exactly that.
>
> **The asymmetry the entry read as an inconsistency is structural.**
> `services.yaml` can forbid because every key in it belongs to the
> process holding the models; `config.yaml` cannot, because it carries a
> region this process does not own. One file, two parsers, neither a
> superset — which is also why `schema_guard`'s posture runs the *other*
> way here: that guard refuses because serving against the wrong schema
> is worse than not serving, and serving with an ignored config key is
> demonstrably not, at a cost of one briefing at the wrong hour.
>
> **What shipped reports and cannot refuse**, settled by the shape of the
> mechanism rather than a flag someone could flip: `core/config_keys.py`
> walks the raw YAML against the model tree and **returns a list**. The
> boot warns and `ReloadReport.unknown_keys` carries it to
> `POST /api/sysadmin/reload` — the surface an operator who has just
> edited the file is actually holding. Live, a real `briefing_hourr: 9`
> in the shipped file came back as
> `{"ok": true, "unknown_keys": ["schedules.briefing_hourr"]}` and the
> reload still delivered everything else.
>
> **The boundary is declared and pinned, never asserted.** `FOREIGN_KEYS`
> names the tray's ten; `sysadmin.core` may not import the tray, so its
> two key lists were lifted to constants and a test asserts the pair
> agree. Exempted **by leaf, not by subtree** — `mute_services` is read
> here, so a subtree exemption would silence `mute_servicess` on the one
> key under that section the backend depends on — which pays a dividend
> nobody asked for: a misspelt *tray-owned* leaf is reported too.
>
> **The check retires and its meaning inverts.** It counted
> `extra="forbid"` on both sides and **this fix moves neither count**, so
> it would have reported *still holds* over a landed closure
> indefinitely — `check_review_schedule_unread`'s defect one entry
> earlier. The detector is re-homed as
> `TestTheAsymmetryIsDeliberateAndStays`, where those counts must now
> **stay** put.
>
> **3079 → 3107**, +28 and 5 retired. Twelve mutations driven, each red
> on the tests about its own rule — and **two passed against
> deliberately broken code first**: the subtree mutation changed nothing
> because `notifications.tray` is not itself in `FOREIGN_KEYS`, and
> adding `ConfigDict(extra="forbid")` to a config model gave a
> *collection error* rather than a red test, since that name is not
> imported there — a stand-in that cannot compile is silence wearing a
> result. `SNAG-CFG-005` is filed for the residue: a typo inside `tray:`
> is dropped by **both** parsers in silence, measured rather than
> assumed, since the tray half was expected to be strict and is not.
>
> *Previously —* **One gate, two answers, and the library's own
> tie-breaker decides it.** estate-manager's message `df4113cb` is
> closed: `core/llm_client.py`'s single `ensure_gpu_idle` read is reached
> by three gates that each have both a waiterless Monday job and a
> request-holding route, so the library's own rule — *a caller that
> cannot answer the question for every invocation keeps the single read*
> — settles it. The split was costed and refused (one narrative every
> forty weeks against a parameter threaded through three signatures) and
> filed in [ideas.md](ideas.md), not declined. Of the six reviews this
> box has generated, **five came from the routes and one from the Monday
> job**, so the docstring calling this inference "deferrable
> housekeeping" was backwards and is gone. 3060 → 3070.
>
> *Previously —* **Twenty-four dead links were three classes, not one, and the middle
> class is the one a plausible path would have made worse.**
> estate-manager's message `25be77ba` is **closed**: all 24 inward links
> in `snag_list.md` (14), `project-capability-audit.md` (8) and
> `tasks.md` (2) resolve, and `tests/test_doc_links.py` is the detector
> that outlives the finding — the estate refused the check under its
> ADR-0073, which is exactly what leaves it here.
>
> **The instruments disagreed by one before a line was repaired, and
> mine was the narrow one.** A first scan found **23**: `line.startswith("    ")`
> treats a six-space *list continuation* as an indented code block, and
> `tasks.md`'s 24th link sits on one. CommonMark makes indentation a code
> block only when no list is open. Repairing on the strength of the first
> reading would have left one behind and reported twenty-four.
>
> **Three fates, and the middle one has no name in the filing.** **5**
> targets survived the 2026-08-08 split and take a path repair. **16**
> left under [ADR-0005](../adr/0005-project-state-leaves.md) and take a
> pointer. **3** are the trap: the *file* survived and the *cited symbol*
> did not — `config.py` lives at `sysadmin/core/config.py` and holds no
> `ProjectsConfig`; `briefing.py` lives at `sysadmin/briefing/data.py`
> and holds neither section builder. Repathing those three would have
> produced links that **resolve**, look right, and point at code that
> does not contain the claim — invisible to every instrument in play.
>
> **The true count is 27, and the estate said so in advance.** Their
> message called 24 a floor because their check is existence-only. A
> superset scan resolving `#L` anchors against the target found **3
> more** that resolve while their anchor has rotted: `main.py:123-128`
> at a blank line, `agent.py:391` at an unrelated docstring,
> `retention.py:85` at `"health_reviews": WHOLE_TABLE`. All three
> repaired.
>
> **No new line anchors were minted**, which is the rule rather than an
> omission. 13 of the 24 carried one and every rotted anchor above was
> once correct; an anchor decays invisibly to an existence check, so
> re-pinning them manufactures more of the defect being repaired. Each
> citation keeps its original line range as *text* — it is the evidence
> the entry rests on — beside a live link to the file.
>
> **3056 → 3060**, +4 and none retired. Two mutations, each red on
> exactly the intended test: a broken link reddens the corpus test, and
> reverting to the naive indentation rule reddens the continuation test
> and nothing else. Docs only — no production behaviour changed; ruff and
> mypy clean, and the snag register parses unmoved at **107 entries, 18
> open**.
>
> *Previously —* **The habit is a guard now, and it caught its author twice before it
> caught anything else.** `SNAG-TEST-002` is **fixed**:
> `TestEveryCheckCanSayItDoesNotKnow` sweeps `CHECKS` and refuses a
> registered check that no test class drives to an `unknown` verdict —
> the fourth sweep over that registry, beside the three asking whether
> the register and the registry agree about *which* entries are
> measured. **18 of 18** covered at the moment of the fix.
>
> **The check retired with the entry and its walk did not**
> (`FROZEN_TABLES`' rule, the sixth time here).
> `check_unknown_branch_unenforced` was written to detect its own fix
> landing, so `_unknown_branch_coverage` and `_unwritable_sentinel` moved
> into the drive and the check, `_sweep_enforces_unknown` and the
> registration went. The register reads **18 open**, every one carrying
> a check.
>
> **The sweep's own class is one of the classes it walks**, which is the
> part no reading would have found. The walk counts a class that names a
> key *and* asserts the verdict, so a docstring citing a check by key
> makes the sweep vouch for that check — itself. It fired on the
> docstring explaining the sweep, and again on the docstring written to
> explain the first firing, for naming the key while saying that naming
> it is what is forbidden. `test_live_drive_premises.py` exempts its own
> owner for this reason; there is no exemption here, so the prose is
> written around the key.
>
> **Two guards passed against deliberately broken code and both were
> repaired.** The second witness — is the class pin green because the
> class is clean, or because the walk is blind *here* — spliced a key
> into the class's real source and **failed**, since this class asserts
> no bare `unknown` constant and could never have been seen; both halves
> are appended now. And the class's name was restated as a constant, so
> pointing it at a *different* clean class left all fourteen green: it
> is derived from `type(self).__name__` instead, which makes that
> mutation impossible rather than merely caught.
>
> **`UNKNOWABLE` is the declaration the entry asked for**, empty by
> measurement — a check whose every input is local discharges the sweep
> by a name and a stated reason rather than by a branch that cannot
> exist, `PRE_CONVENTION`'s shape one file over, with tripwires for a
> stale name, an orphaned one and one with no reason. Driven at a
> stand-in, because a mechanism with no members is `SNAG-UNITS-006`'s
> standing.
>
> **The looseness is stated rather than tightened.** The walk keys on the
> class, so a class naming a key in passing counts —
> `TestChecksAgainstTheLiveBox` covers seven at once. Measured: **no key
> is covered only incidentally**. It is a floor on the habit, which is
> the measurement the entry named being promoted rather than a stronger
> claim invented in its place.
>
> **3055 → 3056**, +14 and 13 retired with the check, arithmetic checked
> against a stashed baseline. Eleven mutations, each red on exactly the
> intended test. One drive-by: the previous sitting moved a
> `# noqa: S404` off `import subprocess` onto `import uuid`, and
> removing the now-unused import would have taken it with it — it is
> back on the line it describes. No production behaviour changed; ruff
> and mypy clean.
>
> *Previously —* **The six pre-convention files were decided one at a time, and it went
> five ways to one.** The handoff asked whether they owe premise
> assertions. **Four owed one and had none**; one owed **the marker and
> never the premise**; one owes nothing. `test_schema_drift.py` is the
> strongest and was settled by driving rather than reading — its whole
> output is `diff == []`, and with `FROZEN_TABLES` widened to cover all
> **13** mapped tables (the blindfold that constant's own docstring
> warns about) `compare_metadata` returns `[]` as well. The guard could
> certify a comparison it had stopped making.
>
> **The witness is the same comparison pointed at an empty `MetaData`**:
> 13 `remove_table` ops normally, **nothing** under the blindfold. The
> other three: `test_schema_guard.py`'s two readers both answer `None`
> for a schema never migrated, so `async_answer == sync_answer` is
> agreement about nothing — and the sibling test in the same class
> already asserted `is not None`. `test_retention.py` owed two, both the
> silent direction the module is about. `test_logs_routes.py`'s
> `stored <= declared` is green over an emptied `log_entries`; measured
> **10 stored inside 15 declared**, five names of slack.
> `test_open_alert_predicate.py` already carried its witness, docstringed
> *"A constant observation is not evidence"* a fortnight before the
> convention existed.
>
> **The exemption is earned now rather than granted**, which is what
> makes the decision recorded rather than remembered. Rule 2's sweep
> accepts a file off the `_live` glob that **marks a premise**, so
> `PRE_CONVENTION` shrank **6 → 1** by five files holding the property
> instead of by five names being trusted. Driven both ways: dropping the
> new clause reports exactly those five, and stripping one file's marker
> reports exactly that file.
>
> **Two falsifications demonstrate the vacuous pass rather than
> describing it.** Under the blindfold the two new premise tests go red
> and `test_models_match_migrated_schema` stays **green**; over an
> emptied `log_entries` the new premise goes red and
> `test_every_stored_source_is_declared` stays green. Seven mutations in
> all, each red on exactly the intended test.
>
> **`SNAG-TEST-002` is the one opening, and it is the exemption's stated
> cost.** `test_snag_claims.py` owes no marker because its premises are
> enforced at the producer — `query_one`'s every way of not-knowing is
> `unknown` rather than `match` — and every registered check is driven to
> that branch by a test in the class that names it. Nothing enforces it,
> so `unknown_branch_unenforced` measures both halves and **caught its
> own author on its first run**, reporting itself as the one check with
> no `unknown` drive. 18 of 18 at filing, **19 of 19** once its own drive
> landed. Its witness needed the same lesson: spelled as a literal, the
> test asserting it wrote the sentinel into the file under the walk and
> two checks were reported covered by a verdict that does not exist —
> `_unwritable_sentinel()` mints one per call.
>
> **3042 → 3055**, +13 and none retired; **3033 → 3042** for the premise
> work, arithmetic checked against a stashed baseline rather than a green
> suite. No production behaviour changed. Ruff and mypy clean.
>
> *Previously —* **The sweep the handoff asked for cannot exist, and the pre-fix file
> is the proof.** `SNAG-TRAY-010` was an **absence**: at `62f8e09`, the
> commit that added it, `tests/test_desktop_store_live.py` named `dnd`
> **zero times**. An AST sweep keys on the *presence* of a token, so this
> one would have been hunting a line nobody wrote.
>
> **Three further measurements, each of which alone settles it.**
> Inverted to *must supply*, the rule is **4 false positives out of 5** —
> only `test_desktop_store_live.py` touches any of the three singletons
> (28 mentions against 0, 0, 0, 0), two of the drives being subprocess
> drives against a real bus and two never reaching `notifier.py` — and
> suppressing those needs the per-file allowlist the rule existed to
> remove. The read is **transitive**, `datetime.now()` sitting in
> `dnd.py:73` inside `is_active` among **27** unsupplied clock reads in
> production, so deciding which a drive reaches is a call-graph analysis
> over `sysadmin/`. And `should_suppress` **already takes a `now=`** it
> does not forward, so a signature-level check reads it as injectable
> and passes.
>
> **The premise assertion is the stronger control, not the weaker one.**
> A sweep answers *did somebody write the supply line* and stays green
> the day the supply stops taking; the premise answers *is the gate open
> now*, which is what the hour decides. `sent_total > 0` catches the
> class, since `min_severity`, `enabled` and a future fourth gate
> silence the announce path identically.
>
> **So the narrower guard shipped instead.**
> `tests/test_live_drive_premises.py`, 15 tests: every
> `tests/test_*_live.py` marks the test — or class — holding its premise
> with `@pytest.mark.premise`, seven markers across the five drives. The
> marker **names the check and never the value**
> (`SNAG-ESTATE-011`'s rule); a name rule was measured first and reaches
> **3 of 5**, because `TestTheHazardIsReal` names what it *proves* and
> `test_failure_replay_live.py` asserts a different premise per test.
> **The glob is a convention, so it is backed by a property**:
> `_opens_a_live_connection` finds the **6** files naming this box's
> database outside the glob, held in `PRE_CONVENTION` and re-asserted
> rather than trusted — without it the premise rule is opt-in by
> filename.
>
> **Three things measurement changed mid-build.** The detector
> **reported itself**, holding the spellings it hunts for, so the owner
> is exempted and then driven at. `addopts = "--strict-markers"` is
> **silently ignored on pytest 9.0.2** — the flag works from the command
> line and does nothing from `addopts` — so a comment claiming it
> enforced something was corrected to the ini option and pinned. And a
> falsification was **destroyed by its own revert**: `git checkout` on an
> uncommitted marker reverted the fix rather than the mutation, so one
> mutation silently re-tested the previous one's condition.
>
> **Seven mutations, each red on exactly the intended test.**
> **3018 → 3033**, +15 and none retired, arithmetic checked rather than
> assumed. No production change; ruff and mypy clean. The six
> pre-convention files are filed as a **task, not a snag** — the
> convention was invented in this sitting, so their exemption is a
> decision to take rather than a defect to record.
>
> *Previously —* **The six reds were the hour, not the tree — `SNAG-TRAY-010` is
> fixed.** `tests/test_desktop_store_live.py` supplies two leaves and
> says so in its own docstring: the transport, and the two clock
> readings. It misses a **third**. `DndManager.is_active` calls
> `datetime.now()` *itself*, so `should_suppress` reads the **real** wall
> clock whatever clock the notifier was handed — and the shipped
> `notifications.dnd.schedule` is `23:00 → 07:00` while the probes are
> raised at `warning`, which `allow_critical` does not exempt.
>
> **Which is why bisecting was a dead end rather than evidence.** The
> entry drove it at `62f8e09`, the commit that added the file, and got
> the same six — correctly. It is not a property of any revision. It is a
> property of the hour: Session 129 committed at **05:27** and wrote its
> handoff at **05:23**. Re-run at **09:37** on the same tree and the same
> commit, the file is **7 passed**, nothing changed.
>
> **The contradiction in the symptom was the discriminator.** *Silent,
> yet the rows are stored and adopted* looks impossible, because
> `_remember` runs only after a successful `send` — except in `_adopt`,
> which writes unconditionally. DND gates `_handle` before the send and
> the `due` filter before `_restate`, and gates adoption **nowhere**, so
> all three probe titles were adopted by a notifier that had never
> spoken. Proved three ways at 09:37 on an unchanged tree: the override
> on gives the six verbatim, off gives seven green, and the **schedule
> itself** widened to `00:00 → 23:59` — the real mechanism rather than a
> proxy for it — also gives the six.
>
> **The measurement the entry named first was right and generalises past
> its own cause.** `sent_total` is in the reading and asserted non-zero.
> Every other speech reading is a `bool` over a **slice** of `sent`, so
> none can separate *the sweep found nothing due* from *a gate above it
> refused everything*; the total can, because a sweep that merely found
> nothing due still leaves the announce-time sends behind it. Driven at
> `min_severity: critical` with DND off — a different gate in the same
> position — it fires, so it catches the class and not the member.
> `dnd_suppressing` is ordered ahead of it so a failure names the gate:
> unfixed, the loudest line was `spoke_unwatched is False`, a sentence
> about the sweep for a fault entirely above it.
>
> **One thing only the falsification found.** At `min_severity:
> critical` the drive **errored** rather than failing — `stored[…]`
> raised `KeyError` while *building* the reading, so the premise test
> written to name the cause never ran and seven errors said nothing. It
> is `.get`-shaped now: absent is a reading, a traceback is not, which is
> this entry's own lesson arriving inside its fix.
>
> **No production change, and that was checked rather than assumed.**
> `desktop.py`'s own comment already states that a suppressed reminder
> does not move the clock, so a fault raised inside the window is
> adopted, anchored, and speaks when the window lifts at 07:00. The
> defect was entirely in what the harness supplied. **3017 → 3018**, +1
> and none retired; three mutations driven, each red on exactly the
> intended guard.
>
> *Previously —* **`wiring` joins `ports`, and admitting it by name alone
> would have
> shipped green and inert.** estate-manager's message `8462bcc5` asked
> whether their hook-wiring check joins `ports` as a second audit check
> this repository speaks for. **Ruled: admitted** —
> [ADR-0006](../adr/0006-wiring-joins-ports.md). Every clause of
> `JUDGED_AUDIT_CHECKS`' ownership test transfers to
> `~/.claude/settings.json`: it is in **no repository at all**, it binds
> all thirteen, the estate may not alert, only the owner can wire it
> (their ADR-0024), nothing here reads `~/.claude` so there is no
> double-count, and they measured on 2026-08-29 that **nobody says it at
> all**.
>
> **The filter is a conjunction, and their message argues about half of
> it.** `wiring` emits **no `breach` at any code** — their ADR-0067 §4
> refuses one — so `JUDGED_AUDIT_CHECK = "wiring"` would have judged
> nothing for ever behind a green suite. Widening
> `JUDGED_AUDIT_SEVERITY` instead re-imports `ports`'
> `claimed_but_silent`, which is availability and already owned here by
> `% unreachable`. `JUDGED_AUDIT_CHECKS` is a **mapping** now,
> `{ports: breach, wiring: warn}`, the only shape in which both stay
> true; `JUDGED_AUDIT_SEVERITY` survives as a name and is **derived**
> from it, pinned by AST because CPython interns the string and a value
> assertion cannot tell derived from retyped.
>
> **Their stale observation was load-bearing, not a footnote.** They
> offered as fact that the comment says "all four" checks emit `breach`
> while the audit runs **twelve**. When every check emitted `breach` a
> single severity constant was unambiguously deference to the producer;
> across twelve checks at three rungs it had acquired a **second job
> nobody argued for** — it was also a check filter.
>
> **Driven against the real producer, because the family ships with zero
> rows.** `estate_service.audit.checks.wiring.run_check` in their venv
> at their commit `003f3bc`, public symbols only, against four specimens
> built from this box's live `~/.claude/settings.json`: clean → **0**
> findings, the 2026-08-25 top-level paste → **4** (one per hook), the
> truncated paste → **1**, `SessionStart` removed → **1**. Through this
> repository's judge: 0, 4, 1, 1 — the last titled `Estate hook
> inbox-notice.sh not wired for SessionStart`, which is their ADR-0068
> §4 condition, spoken.
>
> **Three things only running it said.** `details['hook']` was right on
> three specimens in four and promised a hook name while delivering a
> **file path** on an unparseable `settings.json` — `UnitFinding.enabled`'s
> trap, caught before shipping and renamed to the producer's own
> `subject`. The partition guard **was not a guard for this family**: all
> four of its tests passed before the wiring titles were added to
> `_every_title`, so `SURFACE_TITLE_PATTERNS` could have lacked `Estate
> hook %` while a row saying every hook on the box is down sat
> unresolvable in `alerts`. And **one falsification passed against
> deliberately broken code** — the `code`-is-never-read test asserted a
> true premise and a true consequence and could distinguish nothing,
> because the recorded findings carry no `code` at all; it needed a
> witness where the two signals *disagree* before the mutation died.
>
> **No roll-up, and that is measured.** The population is bounded by the
> estate's own `hooks/` directory — four scripts, one event each — and
> the collapse case is already the producer's, which short-circuits an
> unparseable file to a single finding. A threshold would be invented
> against a population that has never exceeded four.
>
> **The suite is 3017**, from 2984: **33 added and none retired**, all in
> `tests/test_estate_judgements.py`. Arithmetic against a stashed HEAD
> rather than a green suite — 90 → 123 in the file and 2984 → 3017 in the
> tree, both deltas 33, which is the only thing that can witness a
> clobber. **6 are red and none are this sitting's**:
> `tests/test_desktop_store_live.py` fails identically at `62f8e09`, the
> commit that added it, so it has never passed here — `SNAG-TRAY-010`.
> *(Fixed 2026-08-30 by Session 130, and the "never passed here" was one
> word wrong: it had never passed **at that hour**. The file was green on
> the same tree at 09:37 — the DND window, above.)*
>
> *Previously —* **A port the sweep never saw and a port it looked
> straight at were one
> answer, and the discriminator had been in the blob for four months.**
> `SNAG-ESTATE-009` was taken on its own terms and **stays open** —
> deliberately, and decided by its own check rather than by argument.
> `PortAttribution.reading()` and `details['attribution']` split the
> **four** reasons `holder` is `None`: `held`, `transient`,
> `unattributed` (the sweep looked and could not name it), `unswept`
> (the sweep ran before this listener started — this entry), `unknown`
> (no usable sweep). Live: `of(5432)` and `of(8110)` are both `None`
> and now read `unattributed` and `unswept`.
>
> **`as_blob` has emitted `unattributed_ports` since Session 26c and no
> consumer read it** — `attribution_from_blob` was written later, for a
> different consumer. This is the **sibling** of the collapse Session 57
> fixed one field over in the same function: that sitting separated a
> session scope from an unattributable socket and left an
> unattributable socket indistinguishable from a port nobody looked at.
> The entry's own "Why P3" bullet has claimed since 2026-08-17 that
> `details['holder']['observed_at']` publishes the evidence's age; the
> check's docstring calls that **vacuous**, because `holder` is `None`
> on exactly the rows that need it. It is not vacuous now.
>
> **The rung did not move, and that refusal is the new one — on
> correctness, where both standing closures were refused on cost.**
> Quietening an unattributed breach because the sweep predates it
> inverts a posture `_attribution` states in writing (*"the enrichment
> is not allowed to become a dependency of the alert"*): a failed
> `observe_listeners` returns **no** listeners, so every port would read
> unswept and the whole family would drop below
> `tray.notify_min_severity` — Session 26b-A's founding defect at full
> scale, as the fix for a seven-hour window.
>
> **Two of the entry's own measurements were wrong and the box said so.**
> The four historic `warning` rows are **not** the mid-window class the
> entry is about: `transient_ports` first reaches a stored blob at
> 2026-08-17 10:07:41, a day after them, so this entry **has never
> observed its own class**. And *"the window is six hours wide"* is the
> **p90** — 83 inter-sweep gaps in 14 days give a **median of 1.30 h**,
> because `agent_first_run_delay_seconds: 60` re-runs every added job on
> each daemon start and this daemon's median life is 1.77 h. The sweep
> runs 10–15 times a day against a nominal 4. Both errors have one root:
> costed from `config.yaml` and the code path rather than from
> `unit_audits`.
>
> **The check had to be widened before its third limb could be removed
> honestly, and the baseline is what caught it.** `annotated` compared
> detail *key sets*, so it saw a key added to the unswept row alone and
> was **blind** to the same key added to every row with a varying value
> — the shape the fix took, since a key present only sometimes is
> `ports_checked`'s collapse one level down. Measured before a line of
> the fix existed: `both rows carry the same detail keys: True`. So the
> check would have reported `match` over a landed fix, which is worse
> than flipping. Widened, it answered `mismatch`; the limb then came
> **out of the verdict** — `a-probe-keys-on-identity-not-a-mutable-field`
> for the second consecutive sitting — and the narrowed check answers
> `match`, which is the honest reading and the answer to whether the
> entry closes.
>
> **13 tests, 10 mutations, one falsification passing against broken
> code.** `test_a_sweep_predating_the_key_cannot_answer` drove a blob
> with no `ok` either, so the `ok` gate returned before the missing-key
> branch it names was ever reached — right value, wrong reason, and the
> mutation survived. Repaired with a successful-sweep-with-no-key
> specimen; re-driven, all ten land red on exactly one intended test. A
> fixture in `test_estate_judge_agent.py` also had to stop modelling a
> database this code no longer talks to: one `execute` answers both the
> open-alert and the sweep query, and its `scalar_one_or_none` returned
> a bare `MagicMock` whose `scanned_at` reached `json.dumps` the moment
> `details` began carrying the evidence's age.
>
> *Previously —* **The tray speaks about a dead backend now, and the
> grace period the
> entry called "the real work" was decided by two instruments that
> disagree about nothing.** `SNAG-TRAY-009` is **fixed**:
> `NotificationPolicy.evaluate_backend_unreachable` behind a
> **300-second** grace, fed by a new `backend_unreachable(float)` tick
> and a tri-state `_was_connected`. Both faces moved together, because
> the entry is right that a fix for one is not half the benefit.
>
> **`max(3 × status_poll_seconds, 300 s)`, and both halves are
> borrowed.** The 3 is `self_monitor.stall_grace_multiplier` — one
> missed observation is merely late — which
> `notifications.desktop.tray_grace_seconds` already applies to a tray
> poll. The 300 is `min_stall_grace_seconds`, whose stated reason in
> `config.yaml` is literally *"so a restart doesn't flag"* the fastest
> agent: this family's noise population, one domain over. **The floor is
> what does the work**, because `status_poll_seconds` is **10** in the
> tray's model and **30** in the shipped file, so the multiple alone
> spans 30–90 s while the daemon startup it must clear does not move
> with the poll interval at all.
>
> **The two populations are 1,400× apart and there is nothing between
> them.** The daemon's journal holds **104 deploy restarts of 2, 3, 12
> or 13 s** in 30 days — max **13 s**, the one 276 s window having a
> `-- Boot --` marker inside it. The tray's own journal, whose `httpx`
> line is logged only on a *successful* `/health`, holds **27**
> unreachable windows across 36,240 polls and **every one is exactly
> 60.0 s** — one missed poll. Against a nearest real fault of **18,235 s**.
> 300 s sits *below* the geometric midpoint (487 s) on purpose: firing
> early costs a toast on each of 104 deploys a month, firing late costs
> minutes of an outage that ran hours.
>
> **"Multiplicative" was understated — the two populations are
> *disjoint*.** Both real outages were **arrivals** (tray started
> 18:34:46 and 14:44:57 against an already-dead daemon), so
> `connection_lost` never fired; every window it *did* fire on was a
> 60 s deploy restart. The transition signal fired **only on noise and
> never once on a fault**.
>
> **The retired check answered `match` against the fixed code**, which is
> the part worth carrying. Its Face 1 predicate asked whether the emit
> sits inside an `if` reading `_was_connected` — **`True` before and
> after**, since the fix keeps the guard and corrects its polarity. Its
> "initialised `False`" predicate matched **two** assignments at HEAD
> (the initialiser *and* one inside `_on_disconnected`), so it was right
> for the wrong reason and went on matching the second. A shape check
> about a defect whose essence is a *value*. Retired with the entry; the
> **corrected** predicate is re-homed in
> `tests/test_tray/test_backend_unreachable.py`.
>
> **17 mutations, 34 tests, one falsification wrong on the first
> attempt.** `test_the_shipped_file_reaches_the_policy` asserted
> `load_tray_config(config.yaml) == the value in config.yaml`, and the
> shipped 300 **is** the model default — green whether or not the loader
> read the file. Deleting the key from `config.py`'s parse loop,
> `SNAG-CFG-001`'s exact shape, survived it. It drives a mutated copy
> carrying a witness value now.
>
> **Driven live, and Face 1 landed at 0.0 s.** Real `ApiClient`,
> `TrayIcon`, policy at the shipped 300 s and real `DbusNotifier` on the
> real session bus, pointed at a dead `127.0.0.1:8599` — an *arrival*.
> `connection_lost` emitted on the first failed poll, silence held
> through 29.6 / 59.6 / 89.6 s, one non-transient `critical` after the
> grace.
>
> *Previously —* **A login-time replay was worth building, and the entry
> that asked for it understated its own benefit by two orders of
> magnitude.**
> `SNAG-SYSD-005` is **fixed**: `sysadmin-replay-failures.service`, a
> user unit wanted by `graphical-session.target`, announces at login
> every unit failure still open. The entry priced the loss as the gap to
> the next login — 24 min at best, 6.1 h at worst. The `alerts` table
> prices it as the life of the row, and only **2** rows exist for all
> **5** firings (three hit the dedup branch): the one row not fixed at
> once stood open **37.73 hours**, of which the login gap is 24 minutes.
> So the replay recovers **37.3 hours of silence**, not 24 minutes of
> lateness. Reading the entry gives the population; querying the table
> gives the cost.
>
> **The room was not empty for most of it, which reranks the entry's own
> framing.** Reconstructed minute by minute: `start-limit-hit` 18:11:15,
> login 18:34:41, tray started 18:34:46 — polled 8500, got nothing, went
> to `IconState.DISCONNECTED` and stayed there. **22.2 of the 37.7
> hours** carried a live graphical session with the tray running and
> silent; only 15.5 were an empty room. "Four of five fired into an
> empty room" is true about *firings* and misleading about *silence*.
> That is **`SNAG-TRAY-009`**, opened here at P2 with its check.
>
> **The blocker the entry deferred on was not one.** It wanted an
> `--unannounced` flag at the announcer first, refusing a flag with no
> reader — right for a *history* predicate. The replay needs a *state*
> one, and `resolve_unit_failures` has exactly one production caller
> (the lifespan), `% failed` sits outside `RESOLVABLE_TITLE_PATTERNS`,
> and retention purges resolved rows only. So an unresolved
> `systemd_onfailure` row already *means* "this unit has not come back".
>
> **Waiting is permitted here and was refused in the announcer; only the
> number changed.** At login the precondition arrives in seconds —
> plasmashell active 14:44:55, target reached 14:44:57, still
> initialising 14:44:58. `WAIT_BUDGET_SECONDS` is **derived**:
> notify-send's own measured 60.08 s bound, so the replay spends exactly
> the patience one blocked call would have, on a mechanism that starts
> no `plasma_waitforname`. Driven against a private bus, a server
> claiming the name at t+2 s is caught at **3.02 s** and the
> notification arrives intact, `urgency=2`, `expire_timeout=0`. The read
> comes **before** the wait, so a clean login costs 0.34 s and no D-Bus
> call at all.
>
> **Two falsifications passed against deliberately broken code and the
> second is the one worth carrying.** Eleven mutations each landed red
> on their intended test. But the live harness's stand-in server printed
> `claimed` and owned nothing a millisecond later — a `BusName` held
> only in a local is garbage-collected on return — and the wait duly
> reported `False`: a fact about the harness reported as a fact about
> the module. The first repair was insufficient the same way, asserting
> the stand-in had *said* `claimed`. The premise now asks the **bus**
> with `busctl`, independent of both subject and harness. Session 125's
> own trap is avoided by construction: a guard mutated to refuse
> everything turns **three** live tests red and skips none.
>
> **22 open, 3 unchecked** — `SNAG-SVC-004`, `SNAG-TEST-003` and
> `SNAG-AGENT-013`. *(2026-09-02, Session 153: 4 → 3 as `SNAG-AGENT-012`
> gained the nineteenth check. `SNAG-AGENT-013` is the sibling filed
> beside it with a measured-zero population — 0 of 31 services set
> `auto_restart` — and a check for it would have to build the leaf
> nobody has set, which is a different shape of drive from this one.)*
>
> *Previously —* **19 open, 1 unchecked** — `SNAG-AGENT-011`, and the check is **owed
> rather than refused**, which is the opposite of `SNAG-TRAY-010`'s
> reason for sitting here. A discriminating witness exists and its shape
> is named in the entry; what is missing is a sitting, and the owner
> directed that it be the next one. *(2026-08-31, Session 142: 20 → 18 as
> `SNAG-SCHED-001` and `SNAG-SCHED-003` closed together — both their
> checks retired with them, a check naming a closed entry being refused
> by the sweep that already guards `CHECKS`, so the count fell on both
> sides at once — then 18 → 19 as `SNAG-AGENT-011` opened. The sweep
> reports it by name at `unknown`, never at `match`, so an unchecked
> entry is visible rather than merely uncounted.)*
>
> *Previously —* **19 open, 1 unchecked** — `SNAG-TRAY-010`, and the check is
> deliberately not owed yet. A check needs a **discriminating witness**,
> and that entry's whole content is that the mechanism is unknown: every
> "did it speak" reading is `False` while the rows are stored, and until
> `len(notifier.sent)` separates *the sweep never ran* from *it ran and
> found nothing due*, any check written now would pin the symptom rather
> than the claim and answer `match` for the wrong reason. Session 119's
> precedent for `SNAG-CFG-003` stands beside it. *(Session 130: the
> deferral was right and the reason it gave was the fix. Adding
> `sent_total` did separate the two — it read **0**, which is only
> reachable above `_handle` — and the entry closed in the same sitting,
> so **18 open, 0 unchecked** and no check was ever owed. A check
> written at the symptom would have pinned the DND window as normal.)*
>
> *Previously —* **Every open entry names a check** — 18 open, **0**
> unchecked. The
> retired `tray_silent_on_arrival` takes the count with it: a check
> outliving its entry is the other half of that pin, and this one had
> stopped discriminating anyway.
>
> Session 200's restart landed at **2026-09-08 14:49:24**, PID
> 2243717 → 2302052 — the **second** restart of this sitting, and the
> reason is worth the line: the first at 14:42:41 deployed the GPU-context
> term and was verified live at 14:47:43, and then a **docstring-only**
> edit to `gpu_context.py` at 14:47:24 — recording why the estate's new
> `card_reset_at` is deliberately not read — moved an mtime the deploy
> check compares. Paid rather than argued with, on Session 181's
> reasoning: resetting an mtime to satisfy a check is the wrong
> direction even when the bytes are inert. Budget checked before paying,
> which `SNAG-SYSD-007` is why: **1** start in the 10-minute window
> against a `StartLimitBurst` of 5. *(First restart 14:42:41, PID
> 79162 → 2243717.)* The **eleventh** consecutive sitting to pay for a
> restart, and the **fifth** of the eleven where the edit was real:
> `sysadmin/monitor/gpu_context.py` is new and `create_app()` reaches it
> through `monitor/agent.py`, so this one is inside the daemon's import
> graph rather than `SNAG-SYSD-009`'s shape. `/health` 200, and the term
> was read out of `service_health` before the second restart was taken.
>
> *(Previously 2026-09-06 07:17:52 by Session 181, PID 64269 → 79162 —
> the **second** restart of that sitting, and the reason
> was the `stash-pop-reports-a-restart-owed` memory observed live: a
> falsification drive rewrote `sysadmin/snag_claims.py` with **identical
> bytes** at 07:13:28, seven minutes after the first restart, and the
> deploy check compares **mtimes**. The claim was a true reading of a
> false question. Paid rather than argued with, because resetting an
> mtime to satisfy a check is the wrong direction even when the bytes
> prove it. *(First restart 07:06:01, PID 1817 → 64269.)* The
> **tenth** consecutive sitting to pay for a restart
> that buys the box nothing and the **fourth** of the ten where the edit
> was real: `sysadmin/snag_claims.py` gained the twenty-first check, and
> it is a console script `create_app()` never imports, so the shape is
> `SNAG-SYSD-008`'s again rather than the mtime family's. Paid anyway,
> because the check's question is about the box and only a restart
> answers it. `/health` 200. *(Previously 2026-09-05 18:28:48 by Session
> 179, PID 2085468 → 2602752, the ninth of the run and the third real
> edit: `sysadmin/vacuous_guards.py` gained the arc reader and the three
> loop rules.)*)*
>
> Previously: restarted at 16:24:42 by Session 177, PID
> 2077357 → 2085468, restart counter **14** — the **eighth**
> consecutive sitting to pay for a restart that buys the box nothing,
> and the second of the eight where the edit was **real**. This sitting
> added `sysadmin/vacuous_guards.py` and cut 168 lines out of
> `sysadmin/snag_claims.py`; both are console scripts `create_app()`
> never imports, so the shape is `SNAG-SYSD-008`'s again and not the
> mtime family's. Paid anyway, since the check's question is about the
> box and only a restart answers it. `/health` 200, and the startup
> sweep for abandoned runs is the one thing a restart here does buy.
> **Twice**, and the second is the interesting one: the first restart at
> 16:17:20 was overtaken by the fix for the declaration-block defect,
> which the gate's own live run found *after* the box had been brought
> level — so the check went red a second time on a real edit rather than
> an mtime, which is the state it exists to report.
>
> Previously: restarted at 13:51:45 by Session 176, PID
> 1478358 → 1898616, restart counter **12** — the **seventh**
> consecutive sitting to pay for a restart that buys the box nothing,
> and the first of the seven where the edit was **real**. The three
> before it were artefacts: a `git stash pop`, a `.bak` restore, a
> hand-reverted mutation, each leaving bytes identical to their commit.
> This sitting genuinely changed `sysadmin/snag_claims.py` — a new
> check and its constants — and the daemon still gains nothing, because
> that module is a console script `create_app()` never imports, which
> Session 171 verified by importing `sysadmin.main` and finding no such
> entry in `sys.modules`. So the shape is `SNAG-SYSD-008`'s and not the
> mtime family's: the deploy check reads the newest `.py` under
> `sysadmin/` and cannot ask which of them the process loads. Paid
> anyway, since the check's question is about the box and only a restart
> answers it. `/health` 200 four seconds after the TERM.
>
> Previously: restarted at 12:39:44 by Session 175, PID
> 1097551 → 1478358, restart counter **11** — the sixth consecutive
> sitting to pay for a restart that buys the box nothing, and the third
> route to one shape. Session 175 edited nothing under `sysadmin/` at
> all: three test files and four roadmap documents. What raised the
> check was `monitor/agent.py`, whose bytes are identical to `9558544`
> and whose mtime moved at 12:30:59 when a falsification drive widened
> the arbitration gate to `if True` and put it back. So the recorded
> `git stash pop` shape had been reached by a `.bak` restore
> (Session 172) and by a hand-reverted mutation, and neither is a
> content change — the honest repair is the restart rather than a
> fabricated mtime.
>
> Previously: restarted at 22:49:11 by Session 172, PID
> 1055352 → 1097551, restart counter **10** — the fifth consecutive
> sitting to pay for a restart that buys the box nothing, and the first
> able to name a second cause for it. Session 172 changed two docstrings
> under `sysadmin/` and nothing else, so the deploy the restart delivers
> is prose; what actually *raised* the check was `ops_claims.py`, whose
> bytes are identical to `305152a` and whose mtime moved at 22:43:32 when
> a mutation drive restored it from its own `.bak`. That is the recorded
> `git stash pop` shape reached by a second route, and it is the deploy
> check being **right about its question** — the box did not serve those
> bytes — while the answer costs a restart nobody needed. Session 171's
> record of the previous restart, below, stands.
>
> Previously: restarted at 21:14:32 by Session 171, PID
> 829338 → 1055352, restart counter **9**. It buys the box nothing and is
> paid anyway, for the **fourth** sitting running: `ops_claims.py` is a
> console script the daemon never imports — verified this time rather
> than repeated, by importing `sysadmin.main` and calling `create_app()`
> and finding no `ops_claims` in `sys.modules` either side — so this is
> owed entirely to the deploy check comparing mtimes over `sysadmin/`,
> rule 4's stated cost, which is one `kill -TERM` and no `sudo`, against
> a check that would otherwise open every future sitting with a `no`
> nobody should act on. Four consecutive payments for one module is
> itself worth noticing: the check cannot ask what the daemon imports,
> and a rule that could would stop being the cheap mtime test rule 4
> chose. *(Previously **16:45:07** by Session 170 and **16:05:31** by
> Session 169, so the box serves
> `SNAG-CFG-006`'s derived read ceiling; PID 621239 → 658806 → 704516,
> twice in one sitting and the second for the same reason. Both were
> well outside the 600 s limiter window `SNAG-SYSD-007` is about, and so
> is this one.)*;
> `/health` 200, clean `log_aggregator` runs with
> `truncated_sources []`. **The fix's own branch is invisible at the
> shipped config and says so**: `severity_filter: info` already admits
> the declared line, so the daemon can only witness *no regression*. The
> branch was driven against the real `journalctl` in-process at the
> narrowed config instead — 32 → 35 stored, 0 → 3 VRAM lines — which is
> where the evidence for it is.
>
> *(Previously **2026-09-04 14:59:43**, by Session 168, so the box
> matched the checkout after `SNAG-DOCS-003`'s deletions; PID 545156 →
> 621239, `/health` 200, restart counter **5** of `StartLimitBurst=5`
> with **zero** restarts inside the 600 s limiter window beforehand — the
> counter is cumulative and the limiter is the window, which
> `SNAG-SYSD-007` is about. Nothing the daemon served changed
> behaviourally then: `snag_claims` is a console script and
> `sysadmin_tray` is not in this process.)* *(Previously **2026-09-04 12:23:38**, to deploy
> Session 166's
> `fold_declared_incidents`, which takes effect only at start; PID
> 435156 → 545156, back in 10 s on `RestartSec`, no `sudo`, restart
> counter 4 of `StartLimitBurst=5` with **zero** restarts inside the
> 600 s limiter window beforehand. **Verified live and untriggered** —
> three `log_aggregator` runs, all `completed`, no
> `log_incident_graph_unread` and no traceback, so the new per-poll
> `unit_relations()` read works in the daemon; steady-state duration
> **0.51 and 0.52 s** against a pre-deploy median of **0.52 s** over 142
> runs, so the fold and the graph read cost nothing measurable. The fold
> itself cannot fire until the next reset, which is `SNAG-LOG-004`'s
> ordering for the fourth time. That reset arrived at 14:58:13 on
> 2026-09-04 and the fold fired: one row naming ten further
> signatures.)*
>
> _Previously restarted at 2026-09-04 10:59:25 to deploy Session 165b's
> both-spellings `CRITICAL_SIGNATURES`, which takes effect only at start;
> PID 427832 → 435156, back in 10 s on `RestartSec`, no `sudo`, restart
> counter 3 of `StartLimitBurst=5`. **Counter 2 was not this sitting's**:
> the daemon exceeded `MemoryMax=512M` at 10:50:15 unprompted and systemd
> restarted it, which is `SNAG-SYSD-008` firing rather than forecasting._
>
> _Previously restarted at 2026-09-03 22:49:29 to deploy Session 164's
> widened kernel `severity_filter` and `CRITICAL_SIGNATURES`, both of
> which take effect only at start; PID 1794 → 131872, back in 10 s on
> `RestartSec`, no `sudo`, restart counter 1 of `StartLimitBurst=5`._
> Verified live either side: `journalctl -k -p 3` returns **0** lines
> carrying `VRAM is lost due to GPU reset!` and `-p 6` returns **1**, and
> that line hits the declared key with `arrives_at` agreeing. The
> previous restart at 18:49:07 was the reboot onto mainline 7.2.2, clean
> journal — **0**
> `ERROR`/`CRITICAL` lines since; PID 416365 → 423232, back in 16 s on
> `Restart=always`, no `sudo`. **Twice this sitting, and the second was
> owed to `git stash pop`.** The first (13:26:56, PID 329947 → 416365)
> deployed `capped_signature`'s discriminator and the HTTP surface was
> read back: **3** cut titles and **2** cut member lines on
> `GET /api/logs/actions`, every one stamped, **0** duplicate titles.
> The second restored nothing — counting the suite per file by stashing
> to HEAD and popping rewrites every `sysadmin/*.py` mtime with
> identical bytes, and the deploy check compares mtimes rather than
> content, so it reported a restart owed over a checkout it was already
> serving. Its own stated cost, met by a technique this repository uses
> deliberately; the pairing had not been recorded. *Previously 12:41:04,
> PID 279728 → 329947, owed to a docstring.* *Before that 11:49:26, PID
> 274133 → 279728, back in 16 s.* **Seven restarts, and the last two were
> owed to this claim rather than to the code** — `sysadmin/snag_claims.py`
> and then `sysadmin/core/abandoned_runs.py`, the latter reverted from a
> mutation `.bak` with byte-identical content and a moved mtime, neither
> imported by anything the daemon loads. That is the documented
> false-positive direction and it cost two of the seven, which is worth
> knowing beside `SNAG-SYSD-007`: the claim's conservatism and the start
> limiter pull against each other. **The fifth was the finding.**
> The start at **11:31:57** (PID 226296 → 258518) was not a `kill -TERM`: Session 160 restarted
> **five** times — the clean reload path, the breach path, the lifespan
> warning path either side of a mutated `services.yaml`, and this claim
> — which tripped `StartLimitBurst=5` inside `StartLimitIntervalSec=600`
> and left the unit `failed` with `start-limit-hit`. That is the Session
> 39 machinery working exactly as designed on a healthy box:
> `sysadmin-failed.service` fired and raised `critical | sysadmin.service
> failed`, and the lifespan resolved it on the next start, which is the
> pairing that makes that row legitimate. **The documented "the restart
> needs no `sudo`" claim is true only while the daemon is running**:
> `kill -TERM` needs none, `systemctl reset-failed` needs none, and the
> `start` from `inactive` that follows needs polkit `auth_admin_keep`
> (measured with `pkcheck --action-id
> org.freedesktop.systemd1.manage-units`), which `sudo -n` cannot supply
> and a session with no agent is refused for. Filed as
> `SNAG-SYSD-007`. *(Session 159b restarted **three** times,
> which is unusual and deliberate: the first two are the live
> verification of `SNAG-DB-006`'s fix — a code path that had never run on
> this box — and the third is this claim. Previously **2026-09-03
> 08:05:58**, PID 1654 → 85280.)* Owed to the claim rather than to the code,
> which is now **four of the last six sittings** (154, 157, 158b, 159; 155
> deployed code the daemon really does import) — Session 159 touched
> `sysadmin/snag_claims.py` to add `check_next_action`, and nothing under
> `sysadmin/` imports that module, so this is Session 158b's paragraph
> below with one more instance under it. *(The box also **rebooted** at
> 07:35:12 and the daemon came up at 07:36:30 on its own; the start-time
> claim was already `no` when this sitting opened, for that reason and
> not for an edit.)* Session 158b touched
> `sysadmin/snag_claims.py` retiring a check, and nothing under
> `sysadmin/` imports that module: measured, its only four mentions there
> are docstring prose, and its single entry point is the
> `sysadmin-check-snags` console script. Three in five is a pattern rather
> than a run of bad luck, and the mechanism is the check's own stated
> cost — it compares file mtimes across all of `sysadmin/`, and the module
> this repository edits most often for register work is one the daemon
> never loads. *(Session 157's restart was
> 20:25:02, and was owed to the claim rather than to the code — it touched
> `sysadmin/snag_claims.py`, which the daemon does not import, so the
> deploy check reported a restart owed on a file it never loads; this is
> Session 154's case exactly and the check's own stated cost, failing in
> the direction that spends a needless `kill -TERM`. The two reads taken
> *inside* the gap (`MainPID=0`, `ActiveState=activating`, `health=000`)
> are the restart window and not a fault, which is the note two sentences
> down read a second time.)* *(Session 155's restart was 17:25:00, and did
> deploy code the daemon imports: `GET /api/services/actions` served
> `action_from` within a second of coming back, `timer_failed` on
> `alfred-career-mail-timer` and `""` on `venture-chat`.)*
> *(Session 154's restart was 16:53:22, and was owed to
> the claim rather than to the code — it touched
> `sysadmin/snag_claims.py`, which the daemon does not import, and the
> check compares file mtimes and cannot know the difference.)* `/health` answered 200 within 24 s, and the two reads
> taken *inside* that window (`MainPID 0`, a `ConnectError` on
> `/health`) are the restart gap and not a fault. *(Session 153's
> restart was 13:06:58.)* *(The unresolved count read **5** at 13:06 and **3** at 13:12
> inside this one sitting — the two `Estate port 311x`/`811x` dev-server
> breaches opening and closing with an editor window, which is the
> volatility this block already records. The block was **not** corrected
> for the transient reading, which is what those bracketed warnings
> above are for.)* *Previously 2026-09-02 11:51:13, twice that sitting,
> to deploy `SNAG-SVC-003`'s step promotion and then the docstrings that
> record why it is one field wide. Previously 2026-09-02 06:46:10, twice that
> sitting too, to deploy* `SNAG-SYSD-006`'s *fold and then the review
> projection that was flattening it back. Previously 2026-09-01 21:03:19, which was owed
> for the same kind of reason as the one before it:* `sysadmin/monitor/agent.py` and
> `sysadmin/estate/client.py` are both loaded by the running daemon, so
> until the restart it was polling `venture-chat` with no idea the
> estate had stopped it. *Previously 2026-08-31 06:55:16, where the
> owed restart broke a run of three:* `sysadmin/core/gpu_lease.py` is imported by all three
> `run_weekly_review` entry points, so the running process genuinely did
> not have the code the reviews now dispatch through. The three sittings
> before it were the mtime check's known blind spot on
> `sysadmin/snag_claims.py`, which the daemon never loads — worth
> recording that the rule's false positives and its true one look
> identical from the check and are separated only by asking what imports
> the changed file.
>
> *Previously — 2026-08-30 20:59:45, and 2026-08-30 19:54:44.* The **first** restart that sitting
> was owed on the merits — `sysadmin/estate/judgements.py` is imported by
> the running application and the predicate it serves changed — and the
> estate judge ran against live 8400 a minute later, reading all four
> surfaces and raising no queue row. The second was the same blind spot
> as above.
>
> *Previously — the restart before it was* **owed by the mtime check and
> not on
> the merits**, which is worth saying plainly: that sitting's only
> backend change is `sysadmin/snag_claims.py`, a console script the
> running application never imports, so nothing the daemon serves moved.
> `check-ops-claims.sh` compares mtimes and cannot know that, and the
> restart is free (`kill -TERM`, `Restart=always`, no `sudo`), so it was
> taken rather than argued about. **The tray restart is the one that
> mattered** — `sysadmin_tray/config.py` is only live once the unit
> restarts, and it came up clean against the real `config.yaml` with
> nothing said, which is this fix shipping untriggered on the box rather
> than in a fixture. *Previously 2026-08-30 16:26:28 — owed on the merits
> and it deployed a new surface*: `sysadmin/core/config_keys.py` and the
> lifespan's key report, so `POST /api/sysadmin/reload` carries
> `unknown_keys`.
> Boot was silent, which is the correct answer and not an absence of
> wiring — the shipped `config.yaml` declares every key it sets once the
> tray's region is exempt, and a live `briefing_hourr: 9` written into
> the real file came straight back from the route.
>
> *Previously —* restarted **2026-08-30 14:29:19**, clean journal — **0**
> `ERROR`/`CRITICAL` lines since. **Owed on the merits, and it deployed
> nothing observable** — which is a third case the previous two did not
> cover. `sysadmin/core/config.py` *is* in the daemon's import graph, so
> the restart was genuinely due; what it carried was the deletion of two
> `SchedulesConfig` fields no code read, so the running process behaves
> identically either side of it. The mtime check and the merits agree
> here for once, and the behaviour still does not move. `/health`
> answered 200 within 13 s on the new pid. *(The 404 seen first was the
> prober's error, not the daemon's: this service serves `/health`, while
> the estate's monitorable-project contract asks for `/api/health` —
> a difference worth not mistaking for an outage.)*
>
> *Previously —* restarted at 2026-08-30 13:53:01, **not owed on the
> merits**: that sitting changed tests and `sysadmin/snag_claims.py`, a
> console script the daemon never imports, so the restart cleared the
> mtime comparison and deployed nothing. That is the stated cost of
> `ops_claims.py` rule 4 — the check asks the state of the box rather
> than the content of the commit, and fails in the direction that costs
> a needless `kill -TERM`.
>
> *Previously —* the restart earlier the same day was **owed on the
> merits**, and it was the deploy (its timestamp is dropped rather than
> restated: two wall clocks inside the parsed region is `ops_claims.py`
> rule 2's *"one figure stated two ways"*, and the check said so within a
> minute of this paragraph being written): `sysadmin/estate/judgements.py` and
> `sysadmin/estate/agent.py` are both in the daemon's import graph, so
> the wiring family reaches the running process only here. 11.6 s of
> downtime. **Verified live and untriggered**, which is the ports
> family's shipping position exactly: the first post-restart
> `estate_judge` run at 05:25:45 completed with `by_surface`
> `audit_findings: 0` and `unread_surfaces: {}` — zero rows because all
> four hooks are wired, not because nothing looked.
> `/health` answers
> **200** <!--check:health-->, `alembic current` reads 018 at the
> packaged head <!--check:schema-->, and `alerts` held 2 unresolved
> rows,
> `Unusual disk / usage` and
> `Project InvestingAssistant next action idle`, **2**
> named here <!--check:open_titles-->.
> *(Re-named 2026-10-18 by Session 384: 4 → 2. `Critical disk usage on
> /` resolved at 21:56:56 when the owner's uninstalls took `/` to 79 %,
> and `Unusual disk / usage` opened at 22:01:52, the anomaly detector
> reading that drop as 6.5σ below the week's mean. Both `Estate port
> … registry breach` rows had resolved before this sitting.)*
> *(Re-named 2026-10-14 by Session 364: 3 → 4. `High disk usage on /`
> stepped up a band: it resolved at 06:12:50 BST and `Critical disk
> usage on /` opened four seconds before it, when a Steam update took
> 21.5 GB (see the block's first paragraph). `Estate port 3400 registry
> breach` opened at 05:43:46, the judge's first run after the reboot; an
> `info` from the estate's `ports` audit, and nothing held 3400 when
> measured at 20:40, so it was a transient holder.)*
> *(Re-named 2026-10-11 by Session 357: 4 → 3. `venture-chat
> unreachable` resolved at 01:17:36, the unit back after the arbiter's
> lease. `Critical disk usage on /` resolved at 02:07:36 and
> `High disk usage on /` opened two seconds before it, so the disk
> stepped down a band rather than recovering.)*
> *(Re-named 2026-10-10 by Session 356, the count unchanged at 4. The
> ImbaBots idle row resolved at 04:50:11. `venture-chat unreachable`
> opened at 16:34:11, eighteen minutes before this sitting's restart, and
> its message says the estate's GPU arbiter stopped the unit under lease
> 161 for the nightly 24B job, so it is the arbiter's to bring back.)*
> *(Re-counted 2026-10-09 14:35 BST by Session 354: 3 → 4. The
> InvestingAssistant row opened at 2026-10-08 22:50:11, an `info` from
> `estate_judge` on that project's idle next action, and is
> InvestingAssistant's to move. Session 354 declared
> `sysadmin-failed.service` and `sysadmin-replay-failures.service`, so
> the unit sweep's findings fall from four to the two `host`
> `deadlock-api-ingest` units.)*
> *(Re-counted 2026-10-08 22:06 BST by Session 353: 4 → 3. The units
> row resolved at 22:05:52, on a sweep run by hand after
> `go-to-market-watch-replies-timer` was declared: four findings are
> under the alert threshold of five. The four left are this
> repository's `sysadmin-failed.service` and
> `sysadmin-replay-failures.service`, and the two system-scope
> `deadlock-api-ingest` units, which the sweep files as `host`.)*
> *(Re-counted 2026-10-08 21:40 BST by Session 352: 7 → 4. The three
> sports analyser rows resolved at 21:39:14, on the first poll after
> their `services.yaml` entries became `monitor: false`; a reload
> applied it, so the daemon start above still holds.)*
> *(Re-counted 2026-10-08 21:15 BST by Session 351: 2 → 7. The three
> sports analyser rows opened together at 2026-10-07 19:38:50: an
> estate session stopped and disabled those units that day on the
> owner's ruling (estate message `fd376758`), and `services.yaml`
> still declares them, so they will stay open until it does not; that
> is a task. The port row opened at 05:43:11: Alfred's uvicorn listens
> on `0.0.0.0:8100`, and the estate's contract gained a `bind:lan`
> marker on 2026-10-07 (their message `0db3617a`) that Alfred's row
> does not carry. That is Alfred's to settle; this repository only
> reports it. The units row opened at 20:50:11, the fourth episode of
> one finding set since 2026-09-09: two of this repository's own units
> (`sysadmin-failed.service`, `sysadmin-replay-failures.service`), one
> of go-to-market's and two `deadlock-api-ingest` units with no
> project. Not traced here.)*
> *(Re-counted 2026-10-02 13:47 BST by Session 326: 3 → 2. The
> `venture-chat unreachable` row opened at 09:04:27 resolved at
> 09:32:02, when the arbiter's lease ended. `Estate queue starved`
> (`estate_judge`, `warning`), opened at 10:08:00 after Session 321's
> count, resolved by itself at 11:07:34. It was the GPU lease wait that
> Session 325 traced, so no action here waits on it.)*
> *(Re-counted 2026-10-02 09:10 BST by Session 321: 3 → 2 → 3. The
> 21:46:04 `venture-chat unreachable` row resolved at 22:25:37, and
> another episode opened at 00:05:34 and resolved at 01:30:37. The open
> one, opened at 09:04:27, says the estate's GPU arbiter stopped the
> unit under lease 107 for go-to-market's persona model. That is a
> planned stop, not a fault. No action here waits on it.)*
> *(Re-counted 2026-10-01 22:05 BST by Session 320: 2 → 3.
> `venture-chat unreachable` is `info` and opened again at 21:46:04 BST,
> a second episode after the one recorded below. Not traced: it is not
> this sitting's concern, and the earlier episode resolved by itself.)*
> *(Re-counted 2026-10-01 20:07 BST by Session 317: 3 → 2. The third
> row was a venture-assistant `Log error` `warning` opened at 14:21:07
> BST, a page fetch in that repository's own discovery pipeline failing
> on a Unicode escape PostgreSQL would not store. Session 312 recorded
> it and did not trace it. It resolved at 14:36:46, fifteen minutes
> later. No action here waited on it, so its resolving leaves nothing
> undone. The ingest-cancellation row
> Session 311 recorded resolved at 13:56:08, and `Project Athenaeum next
> action idle` at 14:18:07.)*
> *(`venture-chat unreachable` was `info` and opened at 2026-09-30
> 22:24:27 BST. systemd stopped the unit cleanly at 22:23:31, with no
> failure logged, four seconds after a GPU queue lease was read on the
> estate. What asked for the stop was not traced; this daemon's restart
> at 22:19:24 did not touch it. It resolved at 2026-10-01 02:49:29
> BST.)*
> *(The 20:28 UTC GPU reset opened 19 rows on 2026-09-30, and all 19
> resolved by 20:47:49 UTC. The 21:37:30 BST reboot opened mosquitto's
> and Alfred's backend's `Failed to start` warnings at 20:38:47 UTC, and
> both resolved at 20:54:48 UTC by the 15-minute quiet window. The
> headline at the top of this file has the account.)*
> *(`llama-server degraded` opened at 2026-09-30 18:05:58 UTC, after the
> 17:50:13 GPU reset: ADR-0007's predicate read Alfred's inference unit
> as holding a GPU context from before the reset. It resolved at
> 20:42:51 UTC, after the reboot restarted that unit.)*
> *(`Project InvestingAssistant next action idle` resolved at 2026-09-28
> 05:26:33.)*
> *(The 11:49 reboot opened three rows at 11:50:19, mosquitto's
> `dumped core` critical and its `Failed to start` warning and Alfred's
> `Failed to start` warning, and all three resolved at 12:06:19 by the
> 15-minute quiet window. Both units had come up on their first retry;
> the headline at the top of this file has the causes.)*
> *(`alfred-evaluate-frequent-timer critical` opened at 15:56:48 while
> Session 279 was writing this and resolved at 16:01:51. It was one
> failed evaluator run at 15:55, `NameError:
> CareerPracticeResurfaceEvent`, which looks like Alfred's code read
> mid-edit. The 16:00 run succeeded. Alfred's to look at, if it recurs.)*
> *(The unit-sweep row `Unmonitored systemd units: 5 findings`, opened
> 2026-09-26 00:07 when estate-manager's `estate-manager-scan-check.timer`
> went live undeclared, resolved at 21:11:20 — the first sweep after
> Session 262's restart, counting with Session 261's declaration in place.)*
> *(`Estate port 3400 registry breach` resolved at 2026-09-24 05:47 — the
> ports family clearing on its own, a fall noted rather than explained.)*
> *(`Project alfred-glance next action idle` resolved before 2026-09-23 22:50 —
> the estate's nudge family clearing on its own, a fall noted rather than
> explained.)*
> *(`Critical disk usage on /` is **new on 2026-09-22 at 18:11**, replacing
> the `High` row this list named before — `/` read 92.3 % against the 90 %
> threshold, and 93 % with 120 GB free when Session 249 wrote this. No
> sitting's work caused it and none has acted on it; it is named so the
> count stays accounted for, not because anything was decided.)*
> *(The fifth is new since 2026-09-13 and is the estate's nudge family
> doing exactly what it is for — a rise, which needs no explaining away;
> `check_alerts`' founding case is the **fall** nobody notices.)*
> *(The sixth arrived 2026-09-18 and was named on 2026-09-20 by Session
> 242, whose own work was elsewhere — the check had been reading `no` for
> two days because preflight prints this block and asserts nothing about
> it. It is **standing, not flapping**, and that was measured rather than
> assumed before an absolute was written down: 2 rows in the seven-day
> window, first seen 2026-09-18, open ever since. A title that oscillates
> belongs in the set-aside sentences below, and this one does not.)*
> *(**The seventh resolved at 18:20 on 2026-09-21 and the count fell
> 7 → 6**, which is `check_alerts`' founding case arriving the day after
> the sentence was written. `Estate port 3401 registry breach` was an
> Astro dev server in `app-code-oss-5162.scope`; it stopped, the next
> sweep found no listener, and the row closed with nothing done — the
> transient holder of `SNAG-ESTATE-009` behaving exactly as that entry
> says, so the fall is a **confirmation** rather than news about the box.
> **It has not re-raised**, so the prediction the old sentence carried —
> that a resolve-and-re-raise would move it to the flapping set below —
> is half-observed, and the title is in neither set until it fires again.
> What the paired specimen showed while it stood is kept, because it is
> the part that does not age: 3400 quietened to `info` because the
> six-hourly sweep had seen it, 3401 speaking at `warning` because it
> started inside a sweep window. Two adjacent ports, one holder shape,
> two rungs, differing only by sweep age — that entry's whole claim, and
> it had never had a paired specimen before.)*
> *(**That pin is the stable set, and two titles flap and are set aside
> from it rather than counted in it** (2026-09-11, Session 216, closing
> `SNAG-DOCS-015`; the convention this replaces is recorded below).
> `High VRAM usage on AMD Radeon RX 7900 XTX` is declared flapping
> <!--check:flapping-->. `Unusual CPU usage` is declared flapping
> <!--check:flapping-->. **Neither sentence states the duty cycle or the
> episode count** (`SNAG-DOCS-025`, closed 2026-09-12): a marker names a
> check and never a value (rule 7), and a figure beside one that does not
> read it is worse than prose, because prose does not claim to have been
> checked. The measurement reaches a reader fresher than any document can
> hold it — `scripts/check-ops-claims.sh` prints *"measured N episode(s),
> open P % of 7 days"* per declared title at every preflight — and it is a
> flapping quantity, so the figures written here on 2026-09-11 were all
> four wrong within a day and the episode count moved again inside the
> sitting that deleted them. Each is set aside by the `alerts` check and
> judged by the `flapping` one, which withdraws the exemption the moment
> a declared title is unresolved for half the window — so nothing is
> dropped, and the *fall* this block exists to notice still moves the
> figure above. `venture-chat unreachable` was measured beside them at
> **11.3 %** across 9 episodes and is deliberately **not** declared: its
> mean episode is 2.1 hours, which is an outage rather than a flap, and
> no sitting has yet been made to re-pin the block by it — a declaration
> is a judgement this document makes and the check only bounds.)*
> *(**Two more were declared flapping mid-sitting, and they are a filed
> entry's live specimens** (2026-09-14, Session 239). `Estate port 3110
> registry breach` was declared flapping. `Estate port 8110 registry
> breach` was declared flapping. *(Both declarations retired 2026-10-01
> by Session 317: each title last resolved at 2026-09-24 19:58:49 BST
> and left the `flapping` check's 7-day window at 19:58 tonight, so
> both markers set nothing aside and read `unknown`. Retiring them loses
> nothing: should an editor's dev server bring either title back, the
> open row is counted by the `alerts` check and reported as a
> mismatch, which is the prompt to declare it again.)*
> Both opened **after** this sitting's own block was written, which is
> the claims checker earning its keep on the sitting writing the claim —
> the second time in five sittings. They are the pair Session 57 named
> when it built `TRANSIENT_HOLDER_SEVERITY`: Alfred's `nuxt dev` and
> `uvicorn --reload`, launched from an editor, correct findings whose
> remedy does not apply. They arrive at `warning` rather than the quiet
> rung because the sweep that would attribute them predates them, which
> is `SNAG-ESTATE-009` exactly — an entry whose population was described
> as measured and which had **never observed its own class** on a
> `warning` row until today. No figure is written here, rule 12: the
> duty cycle is what makes the declaration honest and it is a flapping
> quantity, so `scripts/check-ops-claims.sh` prints it fresher than this
> document can hold it. They are declarations rather than names in the
> pin because a transient holder leaves on its own — unlike
> `venture-chat unreachable`, measured beside them and deliberately not
> declared, whose episodes are outages.)*
> *(**The fifth resolved, and this note predicted that it would**
> (re-pinned 2026-09-10, Session 208). `Unusual RAM usage` was raised at
> **21:25:49 on 2026-09-09**, after Session 206's block was written and
> while its documents were being checked, which is the claims checker
> earning its keep on the sitting that was writing the claim. It is an
> anomaly row, and `Unusual % usage` is one of the three families
> `_resolve_recovered` deliberately excludes because `_check_anomalies`
> resolves it **by id** — so the fall is expected movement rather than
> drift, the same shape as the `amdgpu` note below and recorded in
> advance for the same reason. That is the second prediction on this
> claim to come true and be re-pinned at the resting state rather than
> re-argued.)*
> *(**The fall this note predicted happened, on the schedule it named**
> (Session 205). The claim read **18** and measures **4**: the thirteen
> `amdgpu` rows resolved together at **13:47:50 on 2026-09-09** — sixteen
> minutes after they were raised, which is `_resolve_quiet`'s
> `alert_quiet_minutes` of 15 doing exactly what it is for — and `Estate
> port 3110 registry breach` resolved at **14:31:49**. So this is the
> **predicted** movement below and not `SNAG-ESTATE-008`'s staleness; the
> figure is re-pinned at the resting state, and what follows is kept
> because it is the reasoning that predicted it correctly.
> **Thirteen of those were one incident and the fall was a resolve, not a
> purge.** `Unmonitored systemd units: 5 findings` closed on its own; the
> thirteen `amdgpu` signatures are a single `gfx_0.0.0` ring timeout,
> page fault and reset at **13:31:38 on 2026-09-09**, raised together by
> the log aggregator's first run after Session 204's restart. **The reset
> succeeded and no `VRAM is lost due to GPU reset!` line was written** —
> measured across the whole journal, not the current boot — so
> `CRITICAL_SIGNATURES` correctly matched nothing and `ADR-0007`'s
> poisoned-context predicate correctly did not fire: `llama-server`,
> `venture-chat` and `venture-embed` all read `ok` afterwards, which is
> right rather than blind. They age out of the window on their own, so a
> fall on this claim is expected movement.)*
> *(**A sixth row, `venture-chat unreachable`, appears and disappears
> with another repository's lease cycle, so a `no` on this claim is
> expected movement rather than drift.** The figure is pinned at the
> resting state, which is the one that holds 87 % of the time. Observed
> across one morning: raised **08:12:05**, resolved **08:32:25**,
> re-raised **09:02:22**. **It is a swap and not a stop**, which the
> first draft of this note under-described: `venture-drain` asks the
> arbiter for the `venture-nightly-24b` profile, and on the grant
> `estate_service.systemd` stops `venture-chat.service` (granite-3.1-8b,
> port 8080) and starts `venture-chat-large.service`
> (mistral-small-3.2-**24b**, port 8083) in its place, reversing both on
> release. Read off the estate's own lines rather than inferred from the
> timing: lease 61 requested 08:09:46, granted 08:09:50 `stopped
> ['venture-chat.service'], started [...]`, released 08:32:15; lease 62
> the same shape at 08:59:17 → 09:07:57. So this monitor reports a
> service unreachable that another repository deliberately stopped, and
> the row opens and closes with the swap. **The 8b is the default-up
> half** — `UnitFileState=enabled`, and 1621 `ok` against 240
> `unreachable` over seven days — while the 24b is the on-demand half,
> `static`, `monitor: false`, and `skipped` on all 1861 of its checks.
> It is `info` rather than
> `warning` because `SNAG-AGENT-011` quietens it under a held lease, so
> it is below `tray.notify_min_severity` and inaudible throughout;
> `SNAG-AGENT-012` holds what that quietening leaves. **A later sitting
> reading `no` here should check
> whether the delta is this one row before treating it as
> `SNAG-ESTATE-008`'s staleness.**)*
> *(The remaining new one was raised by **this sitting's restart**, at 08:18:23, and
> is a pre-existing condition rather than a new one: every added job
> re-runs on a daemon start, so the six-hourly unit sweep fired and
> reported 3 unmonitored units and 2 host units — `orphaned: 0` and
> **`armed: 0`**, which is the half that would have mattered. Ordinary
> debt, and the count is `SNAG-ESTATE-001`'s roll-up, which is why the
> armed split exists beside it.)*
> *(The fifth opened at **08:12:05 on 2026-09-09**, five minutes before
> this sitting's restart and not caused by it: the estate's arbiter
> granted `venture-nightly-24b` a lease at 08:09:50 and stopped
> `venture-chat.service` cleanly to free the card, so the row is
> `SNAG-AGENT-012`/`SNAG-AGENT-013`'s class — this monitor reporting a
> service unreachable that another repository deliberately stopped —
> and not a fault of the box. It sits at `info`, below
> `tray.notify_min_severity`, so it is recorded and inaudible.)* *(**3 → 5 → 4 → 3** across
> Session 181's sitting and not one of the moves this sitting's doing:
> the VRAM row came back for a sixth time, Athenaeum's nudge is the
> estate's taken verbatim, `Estate port 3110 registry breach` resolved
> at 07:07:04 — a minute after the first restart — and the VRAM row
> resolved at **07:29:55**, five minutes after the commit that recorded
> it. So the block was true when written and stale before the sitting
> stopped, which is `SNAG-ESTATE-008`'s founding case reproduced twice
> in one morning and caught both times by the **fall** note this gate
> exists for.)* *(**The fourth reading is deliberately not written
> down.** At the re-measure `Unusual CPU usage` was open — raised
> 07:37:54 by the sitting's own 115-second full-suite run under
> `coverage --branch` and resolved by `_check_anomalies` at 07:42:58,
> one poll later, exactly as its 06:51:52 → 06:56:56 twin had done an
> hour earlier. That is a figure about the instrument and not about the
> box: Session 175's precedent, held here for its reason, and the wait
> for the poll is what made recording the box possible rather than
> recording the measuring of it.)* *(**4 → 3 → 5 → 3** inside
> Session 178's own sitting, and the VRAM row is three of those four
> moves. It was open at preflight with both halves of the pair firing —
> the count rose *and* the marked sentence did not name it — was written
> in, resolved for a fifth time, re-opened, and had resolved again by the
> close. **The 5 is the one reading not to write down**: it carried
> `Unusual CPU usage`, raised by this sitting's own five full-suite runs
> and resolved by `_check_anomalies` on the next poll, which is a figure
> about the instrument and not about the box — Session 175's precedent,
> held here for its reason. The block was corrected twice and settled at
> what the close measured.)* *(**3 → 4**
> again between Session
> 173's close and Session 174's preflight, which is the third crossing
> of that threshold in three sittings and the second time the VRAM row
> has been the one moving. Both halves of the pair fired this time — the
> count rose *and* the marked sentence failed to name the new row — which
> is the direction the finer half exists for and the direction the fall
> note is silent in. It fell back to **3** before Session 175's
> preflight, the VRAM row resolving a fourth time, and this crossing was
> found by the fall note alone — `check_open_titles` read `ok` reading
> *3 named, 3 open*, because a title the sentence names that has since
> resolved is not an unnamed open row.)* *(**3 → 4 → 3** inside Session
> 172's own sitting, which is the pair doing exactly what it was built
> for. The VRAM row rose at 22:33:34 and was named; it resolved at
> 22:50:17 and the count was corrected again — and the second correction
> was found by `check_alerts`' **fall** note, `SNAG-ESTATE-008`'s
> founding case, firing on a live row rather than on a fixture. Note
> which of the two moved: the fall left `check_open_titles` reading
> `ok`, because naming a row that has since resolved is not an unnamed
> open row, so the finer half is silent in exactly the direction the
> count is loud. That row is the log aggregator's, an **event** family
> resolved by `alert_quiet_minutes` after 15 minutes' silence — three
> occurrences on 2026-09-04, at 14:58:40, 15:29:46 and 22:33:34, each
> living about a quarter of an hour — so its absence from a steady-state
> block is the normal reading and not a row anyone closed.)* *(**4 → 3**
> at some point before
> 21:00 on 2026-09-04: the VRAM row resolved again, the card being
> shared by four services and the threshold crossed in both directions
> twice in two sittings. Caught by `check_alerts`' fall note, which is
> the founding case, and the named list corrected in the same edit —
> the two claims move together or `check_open_titles` reports the
> difference.)* *(the VRAM row **flapped inside
> one sitting** — resolved 15:52:37 on the first sysadmin run after
> Session 169's restart, re-raised 16:02:35 ten minutes later, the card
> being shared by four services and the threshold being crossed in both
> directions; a fall and a rise in one afternoon, each caught by
> `check_alerts` and neither by anything else.)* *(the block named `GPU
> was reset — every client lost its VRAM` as its fourth from 14:58 until
> this sitting, while the row actually open carried the VRAM-usage
> title. Corrected by hand, and `check_open_titles` said `match`
> throughout — which is `SNAG-ESTATE-016`, filed today: the substring
> test runs over the whole 178 kB printed region, so a title any past
> sitting wrote down satisfies it for ever.)* *(3 until 14:58 on 2026-09-04,
> when a **genuine** amdgpu MODE1 reset opened the fourth — journal rows
> at 14:58:13 on kernel `7.2.2-arch1-1`, the second reset of the day,
> and not a resume-boundary re-read: it predates Session 168's 14:59:43
> restart by 90 s and was raised by the process that died. It is
> `SNAG-LOG-015`'s fix observed live and unplanned — **one** row reading
> "One incident: 10 further signature(s)" where the 10:36 outbreak below
> opened eleven.)* *(4 until 2026-09-04 — `Estate
> hook session-notice.sh not wired for Notification` resolved itself,
> which is `check_alerts`' fall note doing its job for the third
> sitting running.)* *(15 at 10:36 on 2026-09-04 — the
> ten `warning` rows one amdgpu MODE1 reset opens, plus the
> `alfred-inference` core dump it caused; all eleven resolved themselves
> by 10:56 on `alert_quiet_minutes`, which is the event family's silence
> rule working and `check_alerts`' fall note catching it.)* *(3 until 2026-09-03 13:26 —
> `Unusual RAM usage` resolved itself across Session 162's restart,
> which is `check_alerts`' fall note doing the job it was written for.)*
>
> **It read 14 an hour ago and the fall is the one this block predicted,
> which is the whole point of writing a prediction into it.** Twelve rows
> opened at **11:33:00**, the first `log_aggregator` run after the daemon
> came back, and none of them happened then: the kernel logged an amdgpu
> ring-reset at **11:24:55**, seven minutes *inside* the 77-minute outage
> this sitting caused (`SNAG-SYSD-007`). So they were a **catch-up read**
> — `_resume_floor()` sizing the window by how long since that source
> last stored a row, across a gap the monitor did not choose, which this
> document has written about at length and never observed doing this job.
> Eleven rows for one fault is `SNAG-AGENT-005`'s design working as
> intended: one per distinct signature, not one per line. The twelfth was
> `Failed to start SysAdmin…`, this sitting's own start-limiter trip
> arriving through the log family.
>
> **The prediction was written at 11:44 and came true at 11:48:50.** These
> are *events*, so silence is their only recovery signal: `_resolve_quiet`
> closes a row unobserved for `alert_quiet_minutes`, **15** here, against
> a last sighting of **11:33:05** — so the block said **2026-09-03 11:48**
> and a count of **2** afterwards, and both are what happened. The
> `expires` marker that carried it is **removed rather than left**, which
> is that family's own rule read forward: after its moment a standing
> prediction reports `unknown` for ever, and a prediction that has been
> measured is no longer one. A fall nobody wrote about in advance is `SNAG-ESTATE-008`'s
> founding case; a fall named before it happened is the mechanism
> working. *(Re-counted 2026-09-03 by Session
> 160 at 11:33. Two rows moved and **both were chased rather than
> counted**: `warning: Unusual RAM usage` resolved itself at 10:04:14 by
> `_check_anomalies`' resolve-by-id, which is the previous block's "it
> clears when the rolling mean catches up" **now confirmed**; and
> `critical | sysadmin.service failed` opened at 10:14:32 when this
> sitting tripped the start limiter and was resolved by the lifespan at
> 11:31:57. So the net fall from 3 to 2 is one genuine recovery and one
> row this sitting both caused and closed — neither is
> `SNAG-ESTATE-008`'s founding case, and saying which is which is what
> that entry exists for. Previously re-counted by Session
> 159b at 08:45. The fall from 4 is the **predicted** one and not
> `SNAG-ESTATE-008`'s founding case: the paragraph below named
> `warning: Estate port 8110 registry breach` as `SNAG-ESTATE-009`
> behaving as filed and said it clears at the next sweep, and it has —
> which is what writing a prediction into the block is for. The RAM row
> is still open at 1h25m, so the same paragraph's "it clears when the
> rolling mean catches up" is **not** yet confirmed and is not claimed
> here.)* *(Re-counted 2026-09-03 by Session
> 159, and **both** new rows are expected to fall — said here so the fall
> is not read as news, which is what this claim's own founding case was.
> The 8110 row is `SNAG-ESTATE-009` behaving as filed: it carries
> `attribution.reading: unswept` against an `observed_at` of 06:37:33, so
> the six-hourly sweep predates the listener and the hourly judge could
> not know it is a dev server — Alfred's `uvicorn --reload`, which
> `TRANSIENT_HOLDER_SEVERITY` would have put at `info`. It clears at the
> next sweep. The RAM row is the reboot: `details` reads
> `direction: below`, `z_score: -4.6`, `value: 7.4` against a
> `mean: 19.73` over `samples: 1878` — RAM usage anomalously **low**
> because 07:35:12 emptied it, which is a correct detection and not a
> fault on the box. It is written into the block rather than waited out,
> departing from Session 158b's rule for the reason that rule gives: at
> **24 minutes** it is 4.7× the 5m16s median lifetime of the 51 resolved
> `Unusual %` rows, so it is not a burst. It clears when the rolling mean
> catches up, and `_check_anomalies` resolves it by id.)* *(Re-counted 2026-09-02 by Session
> 158, four hours after the re-count below and the same direction — a
> **fall**, `SNAG-ESTATE-008`'s founding case twice in one day. The
> departure is the `critical` the paragraph below calls Alfred's to
> close, and Alfred closed it: `alfred-career-mail.service` was run by
> hand at **20:47:54**, finished `Result=success` with `ExecMainStatus=0`,
> and `_resolve_recovered` closed the row unaided at **20:50:08** on the
> first healthy poll. The timer's `last_run` is **unchanged** at
> `Wed 2026-09-02 08:20:00 BST` — the timer never fired, and what the
> check reads since `SNAG-SYSD-005` is the service's result rather than
> the timer's, which is that fix demonstrated on a fault it created the
> visibility for. **Whether the repair holds is not measured yet and is
> deliberately not claimed**: the evidence is one hand-run success, and
> the next *scheduled* firing at 08:20 is the first observation the
> timer itself supplies, so a sitting re-counting before then reads the
> same 2 and must not read it as confirmation.)* *(A third row —
> `warning: Unusual CPU usage` — opened at **21:20:04** while this block
> was being rewritten and is deliberately **not** counted into the figure
> above. That family is resolved by id in `_check_anomalies` and its
> historic rows have a **5m08s median lifetime across 37 of them**
> (min 5m02s, max 1h15m), which is exactly the volatility the paragraph
> below says to write the **steady** figure through, and a rise is the
> direction that costs nothing — it is the *fall* that reads as "an
> action this block asks for may already be done". It cleared at
> **21:30:04**, on the first `sysadmin` run after the restart, and *why
> it outlived its own median is the restart rather than the CPU*: that
> agent has no first-run delay, so a `kill -TERM` resets the 300 s cycle
> and nothing re-measured the anomaly between 21:25:02 and 21:30:04.
> A sitting that restarts the daemon should expect every by-id-resolved
> family to look stuck for one interval, which is an artefact of the
> restart and not a fault.)* *(Re-counted 2026-09-02 by Session
> 149; the block said 5 and the checker read 3 — `SNAG-ESTATE-008`'s
> founding case, a **fall**, which is the direction that reads as
> "an action this block asks for may already be done". Both departures
> are `info` rows whose subject went away rather than fixes: the
> nightly arbitrated `venture-chat` swap resolved at its usual hour, and
> the transient dev-server port holder closed when the editor window
> did. Session 148 counted 5 the same morning, so the two families that
> produced the rise it recorded are the two that produced this fall.)* *(The critical is Session 147's,
> and it is a **rise the monitor caused rather than a fault that
> began**: the job had been failing intermittently across 20 days and only became sayable
> when `SNAG-SYSD-005` was fixed. It is Alfred's to close, not ours. Its
> twin — `pgbackrest-backup-timer critical` — was raised at 21:08,
> the unit was repaired at 22:19–22:29, and `_resolve_recovered` closed
> the row unaided at **22:33:29** on the first healthy poll. That is the
> whole family demonstrated end to end in 85 minutes on a fault that had
> stood since March, which is the strongest evidence this sitting
> produced that the fix works.)* *(Session 146 saw the same
> volatility Session 144 recorded and from the same source: the count
> read 1, then 2, then 1 again inside one sitting, the second row being
> `High VRAM usage on AMD Radeon RX 7900 XTX` — **5** rows created on
> 2026-09-01 between 16:06 and 20:31, each opening and resolving. So the
> figure to write here is the **steady** one; a sitting that re-measures
> during a GPU burst will read 2 and should not correct the block for
> it. The falling half is the one that matters and is why the check
> notes a fall at all.)* *(Re-measured **three** times on
> 2026-08-31 by Session 144, which is the finding rather than any of the
> three readings: the count went 1 → 2 → 1 inside one sitting, and
> `venture-chat unreachable` has **4** rows created today. So the row is
> flapping, and a stated figure about it is stale within minutes by
> construction — which is why this sentence now names the **stable**
> member and treats the critical as a transition rather than a state.
> `check_open_titles` is what held still throughout: the count moved
> twice while the *names* stayed answerable, which is exactly the
> finer-half argument that check was written on. Previously
> re-measured twice on 2026-08-31
> by Session 142, and the second reading is `ops_claims.py` rule 5's
> founding **fall** case happening inside one sitting: the block was
> written saying 2 while `critical: venture-chat unreachable` stood, and
> the checker reported one fewer row half an hour later because it had
> resolved on the first healthy poll — exactly as the entry filed for it
> says all 181 of its predecessors did. The row is the **third**
> consecutive sitting to be narrated here, which is the signal rather
> than the state.
> It is a true observation of an arbitrated swap: lease 42
> (`venture-nightly-24b`) stopped `venture-chat.service` at 07:26:01 and
> restored it at 07:31:01, and this row will resolve on the next healthy
> poll as its 180 predecessors did. What makes it worth a snag rather
> than a fourth paragraph is the **nightly** instance: measured over five
> consecutive nights it opens just after 00:00 and resolves at ~05:48,
> open for **5h45m to the second** — the drain's hold — at `critical`,
> the one severity the tray leaves on screen. 181 rows all-time, every
> one `critical`, every one resolved. **Filed as `SNAG-AGENT-011`**
> rather than narrated a fourth time — and the figures in that entry are
> the current regime's 20 rows, not the all-time 181, because 161 of
> those fall on 2026-08-11 → 08-14 under a mechanism the estate's queue
> replaced.
> Previously re-measured 2026-08-30 by
> Session 137: this is a **swap** — the count held at 1 while the row
> changed, which is exactly what `check_open_titles` exists for and what
> `check_alerts` alone cannot see. `venture-chat unreachable` resolved
> and the disk row opened; the disk has been the standing figure on this
> box for weeks, so this is a threshold row rather than news. Previously
> re-measured by Session 136: the row was **open again** — another
> repository's service, reported correctly, and this is the **rise**
> case rather than
> `ops_claims.py` rule 5's fall. It is named rather than counted, which
> is what `check_open_titles` exists for: a swap holds the count still
> while the sentence about *which* row is open goes wrong. Previously
> **1**, `critical: venture-chat unreachable` — another repository's
> service, reported correctly and
> since recovered. Corrected 2026-08-30 by Session 130 off
> `check-ops-claims.sh`, which is the **fall** case `ops_claims.py` rule
> 5 exists for: equality or a rise is the rule anyone would write, and a
> row resolving itself while four documents go on asking about it is the
> founding case. It was already stale at `a2f8deb` — verified by
> stashing — so it is not this sitting's, and it is fixed here because
> the check named it and a document nobody corrects is `SNAG-ESTATE-008`
> reopening.)*
>
> **Alembic head is 019**<!--check:migration_head--> since 2026-10-13,
> when Session 359's migration constrained the open-alert identity
> (`SNAG-DB-007`). The sitting this paragraph belongs to moved none: a
> user unit and a console script move no schema.
>
> **The suite is 2971**, from 2937: **34 added and none retired**, all in
> the new `tests/test_tray/test_backend_unreachable.py`. Arithmetic
> against the baseline rather than a green suite, which cannot witness
> tests that no longer exist — 2937 collected with the new file ignored.
>
> *Previously —* **The suite was 2937**, from 2899: 38 added and none
> retired, in `tests/test_failure_replay.py` (26),
> `tests/test_failure_replay_live.py` (5) and `tests/test_systemd_units.py` (7).


> *Previously —* **A check written for one entry found the entry's own trap in its own
> hand.** `SNAG-CFG-003` is measured and holds: driven at the real
> `reload_configuration` with the daemon's injected syncer, a violating
> configuration installs with `ok=True`, `requires_restart=[]` and
> `jobs_retimed`, at a sum of 25 against a `reminder_hours` of 24. Its
> **cost** is the smaller half three times over — **2 reloads against
> 122 daemon starts** in 30 days, so the fix bullet's question about
> `reload.py` is aimed at the rarest installer; **1 of about thirty**
> suite-only coherence guards over the two shipped files; and **one of
> three leaves**, the other two being invisible to the report and
> installed by a different process. The entry is the **last of the
> nineteen to gain a check**, and every open entry now names one.
>
> Building it hit `load_config` — which is `set_config(parse_config(…))`
> and therefore **installs** — so the drive's own helper was writing the
> value its witness read back, and a mutation swapping the two changed
> nothing. The same trap was live in the guard the entry is about:
> `_reminder_ceiling` left the process holding the configuration its own
> class exists to refuse. Both now read with `parse_config`, both pinned.
>
> **`SNAG-SYSD-004` opened**: `sysadmin-failed.service` has been `failed`
> since 2026-08-23, **4 of 4** firings killed at `TimeoutStartSec=30`
> inside `notify-send`. `Linger=yes` creates the session bus at boot, so
> the script's socket guard passes with nobody logged in. Silent in the
> case it exists for.

> *Previously —* **The cost an entry states is a claim like any other, and this one was
> the smaller half twice.** `SNAG-LOG-014` prices its whole cost at *"a
> count of `alert_raised` that is 2 too high for three days"* on
> `GET /api/logs/trends`. `build_trend_report`'s own docstring says the
> advice **must** be computed off the same report the trend serves, so
> that the two surfaces cannot disagree about whether a signature is new
> — which makes an error in the grouped counts reach both by
> construction. The entry names one of them. Nothing was deleted and the
> remedy judgement stands; what moved is what the register says the cost
> is.
>
> **Driven through the real pipeline against the live table in a
> rolled-back transaction, stored against true.** `/api/logs/trends`
> moves four figures rather than one — `previous` 23→21, `total` 91→89,
> `ratio` 2.96→3.24, `sources[].previous_warnings` 28→26. And
> `GET /api/logs/actions`, which the entry never mentions, carries the
> error in a **title**: the live row reads `sysadmin.service fault up
> 3.0x — "alert_raised"` against a true `3.2x`. `SNAG-LOG-010` is the
> entry that made a title this surface's row identity, so the same
> cap-and-count family has reached the field it was written to protect.
>
> **The duration is wrong in the field the entry offers as the
> mitigation.** `previous` is windowed and does converge on 2026-08-31
> as filed. `total` is `func.count()` with **no window filter**, so it
> stays 2 high until retention — on `ingested_at`, not `logged_at` —
> puts both copies at **2026-09-16**. Eighteen days, not three, in the
> one served figure the bullet points a reader at as evidence.
>
> **What it does not reach is measured, not assumed.** The alert family
> is untouched: both copies are `warning`, `FAULT_SEVERITIES` is
> `("error", "critical")`, and `details['occurrences']` is accumulated
> from what a run read rather than queried — so no row, no fingerprint,
> no toast. The weekly review and the 06:00 briefing are clean, the
> facts section and the prompt byte-identical either side of the
> counterfactual. `/api/logs/stats` and `/api/logs/recent` cap `hours`
> at 168 against rows twelve days old.
>
> **The instrument was keyed on the column the fix rewrote, and this
> entry is the best evidence against that.** `check_duplicate_ingest_`
> `residue` grouped on `(source, logged_at, message)` — and these two
> rows were invisible for eleven days precisely because `SNAG-LOG-008`'s
> backfill had not yet made the copies agree. The **verdict** stays on
> the narrow key, because a wider one admits a microsecond coincidence
> and would hold `match` open after the pair aged out, which is the
> calendar keeping an entry alive rather than closing one. The **"is it
> happening elsewhere"** limb reaches no verdict and moves to the
> record's own identity, `(source, logged_at)`, which is the limb whose
> blindness costs something: a second occurrence needs a restart, and a
> restart is when a declaration changes.
>
> **Measured before it was preferred**: **0 of 235,230 rows across 9
> sources** have two distinct records sharing a `(source, logged_at)`,
> so the `message` component is doing no work today — and the tightest
> gap between two genuinely distinct records is **3 µs, at `kernel`**,
> not the millisecond of `alert_raised` writes the entry's fix bullet
> named as the deciding population. That bullet was 333× wide and at
> the wrong source; it now carries the number.
>
> Session 122's `Unusual CPU usage` row resolved itself by id exactly as
> that block predicted it would, which is why that sitting opened
> reading `no`. The standing deploy, health, schema, alert and suite
> figures have moved to the current block above — stated once, because a
> block giving one figure two ways reads as `unknown`, which is
> `ops_claims` rule 2 and `SNAG-ESTATE-008`'s whole shape.


## Quick Status

| Area | Status | Notes |
|------|--------|-------|
| Backend | 🟢 Complete | FastAPI + 5 agents + scheduler + DB |
| API | 🟢 Complete | <!--check:routes-->**53 routes** *(re-counted 2026-10-15 after Session 371 served `GET /api/games/spans`: 52 → 53. Re-counted 2026-09-27 after Session 268 served `GET /api/health` beside `/health`: 51 → 52. Re-counted live 2026-08-25 after Session 79 added `GET /api/sysadmin/review` and `POST /api/sysadmin/review/generate`: 49 → 51. Session 78 took 48 → 49 with `GET /api/services/actions`. Previously 46 → 48 on 2026-08-24 after Session 75, the two `410 Gone` tombstones for `/api/logs/summary` and `/summary/history`. They are `include_in_schema=False`, so `/docs` lists 46 — `measure_routes()` counts `APIRoute` objects rather than schema entries, which is the honest figure and the one that moves when a route is declared)* across 8 routers plus 2 defined in `create_app` (`scan-all` and `reload`, which need `app.state`); bearer-token auth on mutating endpoints (GETs open). *Counted live 2026-08-17 off `create_app()`; 44 before Session 27 added `GET /api/logs/trends` and `GET /api/logs/actions`* |
| Database | 🟢 Complete | <!--check:tables-->**15 tables** in sysadmin schema (16 counting `alembic_version`; re-counted live 2026-10-15), Alembic migrations (head **021**<!--check:migration_head-->, applied 2026-10-15 — drops `idx_alerts_open_by_agent`, which 019's unique index made redundant. *020 the same day* — `game_spans` and `game_focus` for ADR-0016, with `game_spans`' `retention_config` row. *019 on 2026-10-13* — the partial unique index on open `(agent, title)` and the two flag/timestamp CHECKs on `alerts`; see `SNAG-DB-007`. *018 on 2026-08-28* — `desktop_notifications`, the understudy's spoken set made durable so a 24-hour reminder is reachable by a daemon whose median life is 1.77 h, with its `retention_config` row in the same migration; see `SNAG-TRAY-008`. *017 on 2026-08-27*, applied 2026-08-27 and dropped by 021 — `idx_alerts_open_by_agent`, the partial index that bounds an agent's open-alert read by its *own* rows rather than by the whole open set; measured worthless on its own and decisive beside `unresolved()`, see `SNAG-AGENT-007`. *016 on 2026-08-25*, applied 2026-08-25 — `health_reviews`, the weekly system health review's own table, with its `retention_config` row in the same migration because the two halves fail in opposite directions. *015 the same day added `reliability_scores.skipped_checks`.*) *014 on 2026-08-24 dropped the three frozen tables.* *Was 14. `project_snapshots`, `project_reviews` and `log_summaries` had no writer since ADR-0005 or Session 69 and are gone with their retention rows, their `TABLE_TIMESTAMP_MAP` entries and the `LogSummary` model. `FROZEN_TABLES` is now empty and deliberately kept — an entry there is a blindfold over the drift guard, so emptying it is what proves the drop rather than a new test* |
| Agents | 🟢 Complete | SysAdmin, File Organiser, Log Aggregator, Service Discovery, **Estate Judge** (2026-08-13). Project Organiser left for the estate's 8400 service on 2026-08-13 and stays in `AGENT_NAMES` only because the constraint is add-only |
| GPU Monitoring | 🟢 Complete | AMD via rocm-smi + sysfs fallback, temp/VRAM alerts |
| Observability | 🟢 Complete | Structured JSON logging + request access logs. *`SNAG-LOG-004` found and fixed 2026-08-17: `read_journal` passed no `-a`, so every record over ~4096 bytes returned `MESSAGE: null` and the aggregator crashed on it — armed by the priority fix below, 0 errors and 146 clean runs away from a permanent blackout. `SNAG-LOG-003` closed the same sitting: `services.yaml` now carries a per-source `format: json` declaration and titles read `Log error: sysadmin-service — scheduler_job_error` rather than 252 characters of JSON.* *`SNAG-AGENT-008` closed 2026-08-17: uvicorn's duplicate access logger silenced (volume half), and every JSON line now carries a `<N>` syslog level prefix with `uvicorn.error` rerouted through the same formatter (priority half). **Live since the 14:10:58 restart** — verified, `log_entries` holds 10 `warning` rows for `sysadmin.service` where it held 0 across nine nights* *`SNAG-LOG-005` fixed 2026-08-17: making the daemon visible to itself gave one fault two speakers, so `COVERED_SIGNATURES` quietens `(sysadmin.service, agent_run_failed)` to `info` with `details['covered_by']` naming `failures.py`, which owns agent-run health and waits for two consecutive failures. Keyed on the producers' own constants; measured at 249 error incidents, of which 34 have no owning family and stay loud.* |
| KDE Tray App | 🟢 Phase 3 Complete | Tray icon + service grid + D-Bus notifications + native dashboard + DND mode + service actions (popup retired 2026-07-24) |
| PA Integration | ⚪ Dormant | Code + tests intact, `personal_assistant.enabled: false` — PA retired 2026-07-24, Alfred has no inbox to POST to |
| Testing | 🟢 **4683 collected** | <!--check:tests-->**4683 backend + tray** *(collected, not passed, and the word is chosen: `pytest --collect-only` counts a skip and a green run does not, so the two figures are free to part — equal at 3892 today with nothing skipped, and recorded at 3318 passed against 3319 collected on an earlier sitting. **Green has an owner and it is not this cell**: `check-vacuous-guards.sh` runs the whole suite at the close and `claude-postflight.sh` raises an issue when it comes back red (`SNAG-TEST-012`), so a second assertion of it here would be the second-owner defect — and it would cost 81.6 s at preflight, which runs no suite at all, against 1.9 s for the count. 4670 + 13 on 2026-10-18, Session 384: **13** in `tests/test_gpu_residency.py`, the GTT eviction term. 4604 + 10 on 2026-10-13, Session 359: **10** in `tests/test_open_alert_constraints_live.py`, migration 019's index and CHECKs driven at the live table; six red against the pre-019 schema. 4601 + 3 on 2026-10-11, Session 358: **3** in `tests/test_alfred_telegram_wiring.py`, one gated on Alfred's Telegram token file and skipped until it exists, and two driving that gate. 4542 + 34 on 2026-10-10, Session 356: **34** in `tests/test_auth.py`, the origin check's 13 per-route refusals, 10 more token refusals because the two token tests now run against all 13 routes rather than 8, three census tests, six behaviour cases and two on `origin_allowed`. 16 go red with the check disabled. 4531 + 11 on 2026-10-04, Session 344: **11** in `tests/test_ops_claims.py`'s `TestTheClockStandsAlone`, an `expires` pin that must stand alone; six red with the helper reverted to a substring test. Sessions 341 to 343 added 6 and left the cell at 4525. 4521 + 4 on 2026-10-04, Session 340: **3** in `tests/test_forecast.py`, a fitted line already past a threshold read as due now, and **1** in `tests/test_file_recommendations.py`, the risk item saying "today"; the three forecast cases red at the pre-fix branch. 4504 + 17 on 2026-10-04, counted by Session 337: **13** in `tests/test_desktop_notifier.py`'s `TestRecovery` (Session 336, which left the cell at 4504), and **4** from Session 337, two route cases in `TestPresenceIsMarkedByTheRoute` beside the one it renamed and two in `TestApiWorkerNamesItself`. 4473 + 31 on 2026-10-02, counted by Session 333: **18** in the new `tests/test_sd_notify.py` (Session 331, the `Type=notify` sender), **5** in `tests/test_systemd_units.py` (Session 332, `Type=notify`, `WatchdogSec=` and the burst arithmetic), and **8** in the new `tests/test_off_loop.py` (Session 333, the advice routes off the event loop); Sessions 331 and 332 left the cell at 4473. 4472 + 1 on 2026-10-02, Session 330: **1** in `tests/test_systemd_units.py`, `test_onfailure_fires_only_at_the_start_limit`, which pins `RestartMode=direct` beside `OnFailure=`; red with the directive deleted. 4469 + 2 on 2026-10-01, Session 320: **2** in `tests/test_event_bus.py`, a failed run and a failed commit each publishing `agent.run` alone; both red at the pre-fix `run()`. 4446 + 23 on 2026-10-01, Session 318: **23** in the new `tests/test_mqtt_alerts.py`, pinning what reaches `estate.bus.publish` (topic, identity, never retained, the real `mosquitto_pub` argv) and the four gates before it (disabled, below the severity floor, a row the run's rollback removed, no credential). 4445 + 1 on 2026-10-01, Session 316: **1** in `tests/test_config_defaults.py`, `test_discovery_depth_defaults_to_the_estates`, which finds a declared repository at level 3 and not a bare clone beside it; red at the old literal 2 (counted here by Session 317, Session 316 having left the cell at 4445). 4443 + 2 on 2026-10-01, Session 312: **2** in `tests/test_llm_client.py` pin that `llm_error` logs llama-server's own `error_message` and `error_type`, and `None` for a body of another shape; both red at the pre-fix handler. 4441 + 2 on 2026-10-01, Session 311: **2** in `tests/test_services_registry.py` — the live JSON witness's `searxng` case, which reads the opening of the shim's current run, and `test_the_startup_read_is_bounded_by_its_window`, which shows that read's `--until` cuts. 4432 + 9 on 2026-10-01, Session 310: **9** in `tests/test_gpu.py` (`TestASuspendedCard`) pin that a runtime-suspended card reads 0 labelled `runtime-pm` on both collector paths, three of them red at the pre-fix `gpu.py`. 4431 + 1 on 2026-10-01, Session 309: **1** in `tests/test_services_registry.py` (`test_every_call_passes_the_configured_depth`) requires every `load_registry` call to pass `config.discovery_depth`, red at the pre-fix `units/router.py`. 4424 + 7 on 2026-10-01, Session 307: **5** in `tests/test_forecast.py` (`TestSecondaryWindow`) pin the disk fit's 7-day secondary window, among them a month whose whole-series slope is negative after a cleanup while the last week climbs, and **1** each in `tests/test_file_recommendations.py` and `tests/test_tray/test_files_widgets.py` pin that a date from the short fit names its window. 4422 + 2 on 2026-10-01, Session 306: **2** in `tests/test_tray_launcher.py` extend its drift check to the installed system units in `/etc/systemd/system`, red at the pre-`3f5af0d` unit that still ordered after `ollama.service`, and give it a negative control that runs in CI. 4416 + 6 on 2026-10-01, Session 304: **6** in the new `tests/test_tray_launcher.py` pin the tray to one launcher, the user unit in git — four went red on the pre-fix tree, among them estate message `633d1a86`'s own finding that the installed unit matched no tracked file. 4426 − 10 on 2026-10-01, Session 303: `SNAG-ESTATE-002` closed, and its check's **10** tests in `tests/test_snag_claims.py` (`TestTheNudgeWordingCheck`, `TestTheNudgeCheckAgainstTheRealProducer`) retired with it. 4424 + 2 on 2026-09-30, Session 301: **2** in `tests/test_config_defaults.py` (`TestTheTrendCapIsOneNumber`) pin the trend cap at the priced 5,000 in the model and the shipped file alike, and setting the file back to 2,000 turns one red. 4416 + 4 + 4 on 2026-09-30, Sessions 296 and 298: **4** in `tests/test_log_trend_windows_live.py` pin which trend counts are windowed (Session 296 left this cell at 4416), and **4** in the new `tests/test_log_trend_cap_live.py` drive the trend cap's stated order, which five mutations turn red. 4406 − 7 + 17 on 2026-09-30, Session 294: the log review keeps to its word limit — the **7** mechanism tests left `tests/test_disk_review.py` with the code and are among the **11** in the new `tests/test_word_limit.py`; **5** in `tests/test_log_review.py` (`TestTheWordLimitIsHeld`) and **1** in `tests/test_disk_review.py` pin the wiring, and bypassing the hold in the log review turns three red. 4390 + 16 on 2026-09-29, Session 293: the disk review keeps to its word limit — **7** in `tests/test_text.py` (`TestTrimToWords`) and **9** in `tests/test_disk_review.py` (`TestHoldToWordLimit`), none retired; restoring the line-break sentence end turns two red, and unwiring the hold from `generate_review` turns one. 4387 + 3 on 2026-09-29, Session 292: an `expires` marker cannot be pinned by a clock its block states in another sentence — all **3** in `tests/test_ops_claims.py` (`TestTheBlockIsItsOwnRegressionTest`), none retired, and all four driven widenings of the pin turn one red. 4388 − 2 + 1 on 2026-09-29, Session 291: `SNAG-ESTATE-005` closed, so its check's **2** tests in `tests/test_snag_claims.py` retired with it, and **1** was added there driving `dropin_blind_spot` to `unknown`, which the coverage sweep had counted only through the retired test's class. 4383 + 5 on 2026-09-28, Session 278: a long traceback keeps its cause in `raw_line` (`SNAG-LOG-019`) — all **5** in `tests/test_raw_line_cap.py`, none retired, and three of the five fail with the cap set back to 2000. 4374 + 9 on 2026-09-28, Session 276: the live notification probe waits for Plasma's `NotificationClosed` (`SNAG-TEST-014`) — all **9** in `tests/test_notify_guard_live.py` (`TestTheCloseIsReadFromPlasmasAnswer`, six functions, one parametrised four ways), none retired, and the two driven mutations each turn one red. 4369 + 5 on 2026-09-27, Session 270: a finished agent run keeps its instance stamp — all **5** in `tests/test_agent_run_recording.py` (`TestAFinishedRowNamesItsProcess`), none retired, and each fails against the mutation it names, including a working SQL `||`. 4364 + 5 on 2026-09-27, Session 268: `GET /api/health` served beside `/health` — **4** in `tests/test_health.py` (both paths parametrised through the two existing request tests, one asserting the two paths answer identically, one asserting this service's own `services.yaml` row polls the contract path) and **1** in `tests/test_logging.py` (the access-log exclusion reaches the new path), so the arithmetic reconciles with nothing to apportion and none was retired. 4329 + 31 on 2026-09-26, Session 262: the estate judge reads `vram_floor` under `nothing_granted` (`SNAG-GPU-006`, estate message `4ef705e8`) — **30** in `tests/test_estate_judgements.py` (`TestTheVramFloorNamesItsOwnLimb`) and **1** live in `tests/test_estate_surface_payloads.py`, so the arithmetic reconciles with nothing to apportion and none was retired. **Ten mutations driven and each lands**, the ones that matter being `<=` for the producer's strict `<`, a transcribed headroom for the published one, and the VRAM limb asked before the busy one, which inverts `Arbiter.tick`'s order. 4323 + 6 on 2026-09-26, Session 261: `estate-manager-scan-check-timer` declared (estate message `6d3dbf47`). All 6 are existing parametrised tests in `tests/test_services_registry.py` reaching the new member of `DECLARED_JSON_SOURCES` and `TIMER_SOURCES`, one of them the live check that its journal really is JSON. Nothing to apportion and none retired. 4272 + 21 on 2026-09-25, Session 259: a partial registry load at every call site, and the estate judge speaking for a refused manifest (`SNAG-SVC-007`) — **10** in `tests/test_estate_judgements.py` (`TestRefusedManifests`), **3** in `tests/test_estate_project_contracts.py` (`TestRecordedRefusedManifests`), **5** in `tests/test_services_registry.py` and **3** in `tests/test_units_api.py`, so the arithmetic reconciles with nothing to apportion and none was retired; `tests/test_routers.py`'s stub gained a required `partial` keyword rather than a sibling. **The refusals are the producer's own**: a new fixture recorded by calling estate-manager's `oversight.attention` at a scratch tree, one tree per cause the library names, and a test pins that the recording covers every cause `estate.registry` defines. **Ten mutations driven and each lands on the test written for it**, including a stripped refused-tree projection in the unit sweep, which reddens the classifier drive where an armed orphan would otherwise have been reported. 4269 + 3 on 2026-09-25, Session 257: `alfred-bus` declared, the one of three health-route sub-statuses the owner took — all 3 in `tests/test_http_expectation.py` (`TestTheBusDeclaration`), so the arithmetic reconciles with nothing to apportion and none was retired; the third pins that the `alfred` entry carries **no** condition, which is the owner's reason for a separate entry and the half a later edit would most easily undo. 4260 + 9 on 2026-09-24, Session 253: a `degraded` alert's message says why (`SNAG-SVC-006`) — **5** in `tests/test_sysadmin_agent.py`, **2** in `tests/test_http_expectation.py` (one test, two parametrised causes: the producer saying stalled and the field the check reads having gone, the two remedies the entry named as opposite), **1** in `tests/test_alert_dedup.py` and **1** in `tests/test_gpu_context.py`, so the arithmetic reconciles with nothing to apportion and none was retired; two existing tests gained an assertion rather than a sibling. **Six mutations driven and each lands**, and the one worth carrying is `REASON_CHARS = 160` — `failures.ERROR_CHARS`, the tray-message ceiling one module over and the obvious reuse — which only the GPU-context drive at the longest unit `services.yaml` declares can see. **The suite is not green and that is not this change**: 11 failures and 5 errors, every one a live test and identical on a clean tree, all tracing to another repository's malformed manifest (`SNAG-SVC-007`). 4238 + 22 on 2026-09-23, Session 252: `expect:` on `kind: http` (estate message `ed301e95`) — all 22 in the new `tests/test_http_expectation.py`, and `tests/test_config_keys.py`'s services-model assertion rewritten in place rather than added to, so the arithmetic reconciles with nothing to apportion and none was retired. 4221 + 17 on 2026-09-22, Session 249: `judge_queue_invariants` reads the estate's `gpu_floor` (estate message `a3923a29`, their ADR-0189) — **16** in `tests/test_estate_judgements.py` (`TestTheFloorNamesTheLimb`, ten tests and one six-way parametrisation) and **1** live in `tests/test_estate_surface_payloads.py`, so the arithmetic reconciles with nothing to apportion and none was retired. **Six mutations driven and each lands on exactly one test**, the two that matter being `>=` for the arbiter's strict `>` and this repository's own constant for the published `threshold_percent` — each names the wrong limb only at a boundary, which is why the boundary is a test. 4205 + 16 on 2026-09-22, Session 248: the GPU collector's utilisation figure moves to the counter the LLM gate reads (`SNAG-GPU-004`) and both paths start naming the PCI device a row describes (`SNAG-GPU-005`) — **10** in `tests/test_gpu.py` (16 → 26), **5** in the new `tests/test_gpu_live.py` and **1** in `tests/test_sysadmin_agent.py` (33 → 34), so the arithmetic reconciles with nothing to apportion and none was retired. **The stub had to be pinned by identity rather than by value**: the fixture carries `GPU use (%)` of 18, so a counter stub returning 18 passes against the unfixed collector, and the number was chosen unequal to either card's. **1 of the 16 can be seen by no assertion about a returned value** — the counter must be sampled *before* the subprocesses are spawned, the entry's own bracketing measurement (sd 0.2 before, 3.1 after, one file) making a post-spawn read a fix that ships green and merely measures less badly, so that test records a call *order*. **5 of the 16 are live and one of those is the only guard against the fix going silently inert**: the slot match is made on `rocm-smi`'s `PCI Bus`, and a tool that dropped `--showbus` would leave every row reverting to the perturbed figure with nothing red — a fixture asserting that key asserts a string somebody typed. **That premise test was itself a second statement of the invocation** and restated the flag list beside the module's until `METRICS_ARGS` was given one home. **Eight mutations driven and each lands on the guard written for it**, including the agent dropping `config.llm.gpu_pci_slot`, which is the wiring that makes the collector and the gate one instrument and which no test of the module could reach. 4199 + 6 on 2026-09-22, Session 246: the field-name ledger gains the **floor** the section ledger got the day before — all 6 in `tests/test_briefing_fields_are_additive.py`, so the arithmetic reconciles with nothing to apportion (`SNAG-BRIEF-007`). **The composition they replace is green under the mutation that breaks it**: this file reads its ledgered keys back off a *render*, honest only while the producer spells them as literals, so turning `Overnight Logs`' `data` into a comprehension leaves the section ledger **entirely green at 21 passed** while reddening three tests here — and that is the shape `Filesystem` has had since 2026-08-11, a *ledgered* section that stopped being one. **1 of the 6 exists because the sibling's floor test is self-asserting and this one is not**: that one renders a single section where its ceiling renders six, while the floored section here serves the same three names under **both** fixtures, so swapping the floor fixture for the ceiling fixture leaves every floor assertion green — a guard's fixture choice is part of its claim, and this one pins that the floor payload is a *strict* subset of the ceiling's. **3 of the 6 measure the two ledgers against each other rather than the producer**, which the empty-population problem forces: a parametrised guard over an empty mapping is green without running, `RETIRED_FIELDS` answers that with a forged retirement and a floor has no forgery, so totality answers it instead — a floored title that cannot be excused must be ledgered. **Six mutations driven, all six land on the intended tests and five are caught nowhere else in the suite.** 4192 + 7 on 2026-09-21, Session 245: the briefing producer's section list gains a **floor** beside its ledger — all 7 in `tests/test_briefing_sections_are_additive.py`, so the arithmetic reconciles with nothing to apportion. **The guard it joins could not have seen this**: both additive-only ledgers drive `_every_branch_taken()`, a payload built to make every conditional true, and a floor is a property of the **empty** case — so what a consumer always receives went unasserted, and in `tests/test_health_review.py` it was rendered and looked straight past, a test that builds exactly this payload and asks only whether one title is absent. **The premise was stated in three places here and the consequence in none**, which is why estate-manager's item was not redundant: `_gather_logs` says it never returns `None`, the comment over the append says a count is always available, and ADR-0014 §2 re-measured the one-unconditional figure on 2026-09-14 — every one about the *producer*, where a floor of one and a guaranteed `type` are about the **payload**. **2 of the 7 measure the fixture rather than the producer**, which the subject forces: a floor fixture that drifts upward leaves a green suite claiming a guarantee the producer does not give. **One of those two was measured empty before it was believed** — it walked the `if` tests for `gathered[...]` subscripts and the producer binds each key to a local first, so it resolved **0** gated keys and passed over any fixture at all; it resolves the alias now and finds **5**, and carries its own anti-vacuity assert. **Eight mutations driven and all eight land, none green**, and the one that matters is `if True:` round the floor section: the drive stays green and only the source walk reddens, which is what separates a floor from a condition that happens to be true. `SNAG-BRIEF-007`. 4195 + 6 − 9 on 2026-09-21, Session 243: `SNAG-LOG-014` closes and its check retires — **the second sitting on this row whose arithmetic does not reconcile with nothing to apportion**, because tests were retired as well as added, and it reconciles anyway: `tests/test_snag_claims.py` loses `TestTheDuplicateIngestCheck`'s 9 and `tests/test_log_resume_boundary.py` gains 6 (8 → 14), net −3. **The detector is re-homed rather than deleted** (`FROZEN_TABLES`' rule) and lands in `SNAG-LOG-007`'s own file, because the residue it counted was that mechanism's. **It is keyed on neither key the entry argued between**: `raw_line` holds the journalctl record verbatim, so one raw line under two rows is one record stored twice and two are two records — which the narrow key cannot see (the recorded form carried different messages) and the wide key gets wrong (a live 0 µs coincidence from `sysadmin.service`). **4 of the 14 measure the instrument rather than the table**, which an empty finding population forces: the live-drive premise `SNAG-TEST-007` rule 2 now binds on this file, the empty-table witness no live run can reach, the statement pin on the key, and the discrimination driven at *both* answers. **Four mutations driven and all four land; one passed against deliberately broken code first** — inverting the discrimination left the file green, its population being the groups that agree about `raw_line` and that population being empty on a healthy box, `SNAG-TEST-010`'s shape, which is why the predicate is named and driven at a fabricated group. **And the restore failed silently before any of that**: the drive's `cp` targeted a scratchpad directory that did not exist, so three mutations stacked and every reading after the first measured the wrong tree — Session 242's own lesson by a second route, an untracked file there and a missing directory here. The restore carries a checksum witness now. 4170 + 25 on 2026-09-20, Session 242: the additive-only ledger goes one level down, from section **titles** to the `data` field names the producer writes as literals — all 25 in `tests/test_briefing_fields_are_additive.py`, a new file, so the arithmetic reconciles with nothing to apportion. **2 of the 25 are skipped and the skip is the finding**: they parametrise over `RETIRED_FIELDS`, which is empty *by measurement* — no field has ever left either ledgered section across the 15 commits that have touched the producer — so a third test drives the same rules at a **synthetic** retirement, an empty population being how a rule gets written wrong and stays green. **4 of the 25 measure the instrument rather than the producer**, which the subject forces: the walk's two premises, the fixture premise, and the one that matters — `render_sections` must still spell the ledgered keys as *literals*, because the guard reads **rendered** keys and the day either section becomes a comprehension those keys start arriving from the fixture and the ledger silently stops measuring anything. That is not hypothetical: `Filesystem` does exactly this today and renders `['total_mb']`, a key the producer never names. **Twelve mutations driven and all twelve land, ten of them on exactly one test**; the two landing on two are right to — forgetting a whole section empties a closed set as well as breaking totality, and dropping a field from the ledger alone is caught by both halves by design. **One mutation was measured wrong before it was measured right**, which is the part worth carrying: the new file is *untracked*, so `git diff` verified nothing between mutations and the restore went unwitnessed — the run reported three reds across two sections where a re-run with the diff printed gives one, the history half. A mutation drive whose restore is not observable measures the previous mutation as often as the current one. `SNAG-BRIEF-006`. 4156 + 14 on 2026-09-15, Session 240: the additive-only guard, `tests/test_briefing_sections_are_additive.py`, all 14 in one new file and none retired — the ledger it introduces is the first assertion here that a briefing **section title** may not simply leave, which the six scenario assertions in `tests/test_briefing.py` could not be, since a commit removing a section edits those alongside it. **Ten mutations driven and none passed green**; three light two tests each and each is right to — dropping a live title is caught by both halves of the ledger by design, a broken fixture breaks its own premise and the render assertion, and crippling the walk breaks both premises about the walk. **One premise had to be decoupled before it could be driven**: it asserted `len(rendered) == len(SERVED_TITLES)`, so it reddened whenever the producer dropped a section — a premise standing in front of its own subject — and it derives the fixture's keys from an `ast` walk of `render_sections` now. 4150 + 6 on 2026-09-14, Session 238: the same guard asked one seam over, at `TrayConfig` against `sysadmin_tray/` — **5** in `tests/test_config_defaults.py` beside its `AppConfig` sibling and **1** in `tests/test_tray/test_config.py`, which is the split rather than a stray: that one guards the *third* half of a tray setting, an allowlist entry with no field, and belongs beside the rule whose complement it is. Nothing to apportion and none retired. **The walker is parameterised rather than copied**: a second implementation of one derivation is `SNAG-DB-003`'s shape, so `_config_field_names` takes the root model and the two guards differ only in *what* they walk and *where* they look for readers. **3 of the 5 measure the instrument rather than the tree**, which the subject forces: the vacuity premise, the container half whose population is empty **twice over** (`TrayConfig` is flat, so there is no container to be unread, where the sibling has 31 and finds none), and a `tokenize` equality asserting that every occurrence of the removed name in the file is a comment. **That last one replaced a first draft that restated the reachability claim one test above** — one fact with two speakers, and unfalsifiable one-to-one, because the mutation that reddens it reddens its sibling. **Six mutations driven and four land on exactly one test**; the two landing on two are right to — the shared helper's premise gives one red per guard, and the original defect restored verbatim reddens the leaf guard beside the comment equality, which is a defect two independent guards catch. 4144 + 6 on 2026-09-14, Session 237: the sweep that trimmed one block becomes a guard over the whole `AppConfig` field tree — all 6 in `tests/test_config_defaults.py`, so the arithmetic reconciles with nothing to apportion, and none was retired. **2 of the 6 measure the instrument rather than the tree**, which the subject forces: a walker that stopped descending would report clean over an emptied population, and a docstring naming a deleted field is what a lexical guard would read as a live one. **Six mutations driven and all six land on exactly one test**, the sixth only after it was sharpened — a sub-config carrying an unread leaf reddens the leaf guard as well, so the control became one whose leaves all have readers and whose container name has none. 4140 + 5 − 1 on 2026-09-14, Session 236: the trimmed `agents.project_organiser` block gains the guard that keeps it trimmed — **the second sitting on this row whose arithmetic does not reconcile with nothing to apportion**, because a test was retired as well as added. `TestTheOrganiserBlockIsTrimmedToItsReaders` arrives with 5 in `tests/test_config_defaults.py` and `test_grade_bands_defaults` leaves it, net +4. **The retirement is the unusual half and it is not the usual rule.** Deleting a guard beside its last finding is what `FROZEN_TABLES` and `test_none_of_them_are_defined_in_contracts` exist to refuse; this one goes because what it guarded cannot come back *here* — `HealthGradeBands` scored repositories, and that scorer left with the projects domain on 2026-08-13 (ADR-0005). **Six mutations driven and one passed against deliberately broken code**: deleting `discovery_depth` from the model is a no-op for a reader that measures `units/agent.py`, so the test asserts the declaration now. A seventh is green **by design** and is `SNAG-CFG-008` — restoring a name-colliding field escapes the model half, whose reach is pinned at **7 of 12** rather than claimed. 4136 + 4 on 2026-09-14, Session 232: the session's audit reader is decided against `ports` and the guard reads the producer's **vocabulary** rather than counting its filings ([ADR-0013](../adr/0013-a-published-key-is-necessary-and-was-never-sufficient.md)) — all 4 in `tests/test_estate_docs_notice.py`, 37 → 41, so the arithmetic reconciles with nothing to apportion. **The two codes the refusal rests on have filed nothing across estate-manager's 430 audit runs**, which is why neither their `GROUP BY` over `audit_findings` nor this repository's own census over `Finding(` could see them, and it is the whole reason the guard is a source walk: `claimed_by_an_unregistered_tree` is `breach` **and** carries `detail.project`, so a reader here would repeat what `JUDGED_AUDIT_CHECKS` already speaks, and `claimed_by_more_than_one_row` names its claimants in `detail.rows[].project` and would be read blind. **Six mutations driven and all six land, four of them on exactly one test**; renaming a `SEVERITY_*` constant reddens the premise beside the overlap test, which is what the premise is for, and adding `docs` to `JUDGED_AUDIT_CHECKS` reddens the control — the one mutation of *our* side rather than theirs. The rung is **composed** from `JUDGED_AUDIT_CHECKS` rather than asserted as `"breach"` on both sides, which would pin a coincidence instead of the conjunction. `ESTATE_TREE` gained an `ESTATE_TREE_OVERRIDE` for the falsification, the script's own `ESTATE_PROJECTS_ROOT` idiom one seam along: a guard about a tree this repository does not own cannot otherwise be driven at a producer that has changed, and a no-op mutation is not a control. 4130 + 6 on 2026-09-13, Session 228: `next_action_line` strips the marker the board reads separately (`SNAG-DOCS-028`) — all 6 in `tests/test_snag_claims.py`, 457 → 463, so the arithmetic reconciles with nothing to apportion. **Five of the six exist because the pin that was already the falsification can only see one of three mutations**: no strip is caught by a marked document, an unanchored strip by today's live line *by accident* (it quotes the marker mid-sentence inside backticks and tomorrow's will not), and a strict mirror of their reader by an unreadable marker **alone** — which no live document carries. **Four mutations driven and each lands on its intended test**, three of them on exactly one. **The sixth is reddened by none of them and says so**: an unmarked line returned byte-identical is the case every green run before today already covered, kept as the regression floor and stated as an empty population rather than dressed up as a control. 4125 − 1 + 6 on 2026-09-13, Session 227: `SNAG-PORT-006`'s pin is re-keyed from the `ss` invocation onto what the estate does with the pids — **the one sitting on this row whose arithmetic does not reconcile with nothing to apportion**, because a test was retired as well as added. `test_the_estate_still_runs_ss_without_p_which_is_why_this_module_exists` leaves `tests/test_unit_ports.py` (83 → 82) and `tests/test_estate_port_join_live.py` arrives with 6, net +5. **3 of the 6 are premises**, the third of them the one that matters: a green *"blinding their directory reader resolves nothing"* is evidence only where the two joins can disagree on this box, and they disagree on **21 of the 29** ports `ss` names a process for. **Four mutations driven and all four land on the right test**, the first modelling the landed fix — a producer with a cgroup fallback reddens both altitudes independently, `attribute` and `run_check`. 4119 + 6 on 2026-09-13, Session 226: `services.yaml`'s two computable comment claims gain the guard `SNAG-DOCS-027` specified — all 6 in `tests/test_services_yaml_live.py`, a new module, so the arithmetic reconciles with nothing to apportion. **3 of the 6 are premises**, which the subject forces rather than a preference: `systemctl show` answers `TriggeredBy=''` for a unit that does not exist, byte-identical to a real unit no timer triggers, so every negative this file believes rests on a reader shown to discriminate — and a reader answering `loaded` to everything leaves the installedness sweep **green**, which is the mutation that settled where the premises go. **Nine mutations driven and all nine land**, one of them the pre-2026-09-13 sentence restored verbatim; the limb with an empty population on this box — a triggered `oneshot` + `RemainAfterExit=yes` unit — was given a real specimen with `systemd-run --user --on-active` rather than left unexercised, because a no-op mutation is not a control. 4097 + 22 on 2026-09-13, Session 224: the estate's three timer journals are read (`ideas.md`'s top entry, promoted and built the same day) — all 22 in `tests/test_services_registry.py`, 56 → 78, so the arithmetic reconciles with nothing to apportion. **3 of the 22 are the pre-existing live witness reaching its new members**, its parametrisation having been pointed at `DECLARED_JSON_SOURCES` so it can never lag the set it witnesses. **Six mutations driven and six killed**, which took two repairs rather than one: the `--since` flag's first draft was inserted between `-u` and the unit, so journalctl took it as the unit name, exited non-zero and **every** live source skipped green — including the one that had passed for weeks — and the newest-record assertion was unfalsifiable until the detector was driven where it must say *no*, `estate-manager-api` being the live negative because the estate leaves `uvicorn.access` outside its formatter on purpose. A skip is not health, so the windowed read is now pinned at this daemon's own unit as a **refusal**. 4093 + 4 on 2026-09-13, Session 223: `tests/test_unit_ports.py` gains `TestATransientHolderIsNotAProject`, four tests pinning ADR-0012's refusal of the fix estate message `11cf5113` proposed — all 4 in the one module, so the arithmetic reconciles with nothing to apportion (`SNAG-PORT-005`). 4087 + 6 on 2026-09-13, Session 222: `README.md`'s moving figures gain the scope their guard never had (`SNAG-DOCS-012`) — all 6 in `tests/test_readme_claims.py`, 30 → 36, so the arithmetic reconciles with nothing to apportion, and the baseline was **collected** rather than read off this cell. **One of the six measures nothing about the document at all**, which is the split the drive forced: five read `README.md`, and `test_the_claim_it_supports_is_still_true_of_the_box` reads the **tree**, because the five figures may each drift inside the band while the comparison between them reverses. **Seven mutations driven and six killed; one passed against deliberately broken code** — restoring the pre-fix figure under today's hedge and date sits at 6.7 % against a 15 % band, filed as `SNAG-DOCS-026` rather than closed, because the band checks a value where the date asserts a provenance. **Two more were insufficient before they were sufficient**: removing one spelling of this row's own checked cell changed nothing, the cell stating the count twice on purpose and `CLAIM_PATTERNS` reading both; and the deferral's first draft asserted readability in a **fixture**, so a removed cell errored every test in the class including the premise written to name the cause. 4083 + 4 on 2026-09-12, Session 221: the two `<!--check:flapping-->` sentences give up the four figures their marker never read (`SNAG-DOCS-025`) and gain the guard that keeps a digit out of them — all 4 in `tests/test_ops_claims.py`, 198 → 202, so the arithmetic reconciles with nothing to apportion. **One of the four is a premise and one is the only one a silent gate reddens**, which is the split the mutations forced rather than a preference: driven four ways, restoring a figure to the document and widening the scope to the region each redden the property test, dropping the code-span exemption reddens it beside the detector drive, and a gate returning nothing at all is caught by that drive alone. 4042 + 8 on 2026-09-12, Session 218: `tests/test_handoff_shape.py` gains rule 3, the gate guard — a published next action may not name a date the document has itself declared under `## Scheduled action` (`SNAG-DOCS-022`/`SNAG-DOCS-023`). All 8 in the one module, so the arithmetic reconciles with nothing to apportion: 16 test functions → 24, 18 collected → 26, the gap being two pre-existing parametrised pairs. **6 of the 8 are synthetic and that is the design rather than a shortfall** — the live document is deliberately compliant, so it can witness neither the rule nor the two false positives the naive rule produces, and those two forgeries (`91fd90e7`'s deadline, `305152a4`'s subject date) are what stop the narrowing being quietly widened back. 4018 + 24 on 2026-09-11, Session 216: the ops-claims block gains rule 12, the flapping declaration (`SNAG-DOCS-015`) — all 24 in `tests/test_ops_claims.py`, so the arithmetic reconciles with nothing to apportion, and the baseline for that file was **174** rather than the 169 a `-k` filter suggested, which is why the total moved 24 and not the 29 a first count claimed: `TestProseWraps` matched the filter and was never new. 4013 + 5 on 2026-09-11, Session 215: `tests/test_doc_links.py` gains containment beside existence (`SNAG-DOCS-020`) — all 5 in the one module, so the arithmetic reconciles with nothing to apportion, and **4 of the 5 are synthetic**, which is the point rather than a shortfall: with every escaping link repaired the corpus assertion is vacuous, and a mutation that makes the detector report nothing reddens zero corpus tests. 4001 + 8 on 2026-09-10, Session 212: `tests/test_by_project_contract.py`, the first test of any kind for `GET /api/services/by-project` — all 8 in the one module, so the arithmetic reconciles with nothing to apportion (`SNAG-DOCS-018`). 3988 + 13 on 2026-09-10, Session 211: the same module gains the **consumer** half of the membership rule — an AST walk of `sysadmin_tray/` pairing each request with the model its reply is handed to — so again all in one module and the arithmetic reconciles with nothing to apportion (`SNAG-DOCS-017`). 3964 + 24 on 2026-09-10, Session 210: `tests/test_claude_md_registry.py` sweeps `CLAUDE.md`'s Contract Registry against `create_app()` both ways, all 24 in the one module, so the arithmetic reconciles with nothing to apportion (`SNAG-DOCS-014`). 3915 + 49 on 2026-09-10, Session 209: `tests/test_readme_claims.py` (24) and `tests/test_docs_index.py` (20) extend the membership sweep to the other two documents that make the claim, and `test_architecture_doc.py` gains 5 pinning its schedule to `plan_jobs` rather than to `README.md`; the arithmetic is stated because it reconciles — 5 + 24 + 20 is the 49, so no file was clobbered by a write (`SNAG-DOCS-013`). 3900 + 15 on 2026-09-10, Session 208: `tests/test_architecture_doc.py`, the
membership guard that outlives `SNAG-DOCS-011` — every package, agent and mapped
table swept **both ways** against `docs/ARCHITECTURE.md`, because the entry
counted lines naming a departed component and a line count cannot measure an
omission. Eight mutations driven and each red on the intended guard, four of them
modelling an omission rather than a phantom. None retired. Previously 3892 + 8 on 2026-09-09, Session 203: five in `tests/test_estate_judgements.py` and three in `tests/test_estate_surface_payloads.py` for the errored-check wording, none retired — ten mutations driven and each red on the intended test, but **three of the eight cannot be reached by a source mutation at all**, being driven at producer-captured fixtures, so they were falsified by mutating the fixture (a field that *would* discriminate the two arms, and the two arms captured at two paths) and by dropping the cap below the measured population. Previously 3888 + 4 on 2026-09-08, Session 202: the symlink-loop guard in `tests/test_hook_wiring.py`, none retired — estate message `f5e450cb` reported that `_where`'s `except OSError` cannot catch the one input that reaches it, since `pathlib.check_eloop` re-raises a loop's errno-40 error as a `RuntimeError`, and three of the four new tests die under both mutants while the fourth pins the four inputs `strict=False` swallows and is meant to die under neither. Previously 3780 + 27 on 2026-09-06, Session 191: **26 written and 1 generated by the registry itself** — `test_each_pattern_requires_the_emphasis` is parametrised over `CLAIM_PATTERNS`, so the commit adding the `tests` key took the suite 3780 → 3781 before this file gained a line, and the check therefore sits **inside its own population**; measured by collecting at HEAD and against the tree and diffing the node ids, which named the one new id exactly. **none retired** — no check retires, because the cell had never carried one. **Eighteen mutations driven and eighteen killed, three of them only after the test that should have caught them was repaired.** Two survived the first drive: loosening `COLLECTED_RE` reddened nothing, because the shape it admits is already refused by the status gate one line up — multiplicative rather than independent, `SNAG-AGENT-008`'s shape, and the road where only the regex can speak is a partial collection exiting **0**, which `--continue-on-collection-errors` in `addopts` would produce; and `"check-vacuous-guards.sh" in region` survived the phrase being taken out of the cell, because the block already mentions that script **7** times, a substring test over an append-only document only ever getting truer. The third was blunt rather than absent: removing the cache errored all 158 tests in the file through the fixture's `cache_clear`, so the statement test written to speak for it never ran — the fixture reaches for the method now and the same mutation reddens exactly the two tests about the cache. **The cache is the sitting's one real cost and it was measured either side**: `snag_claims.ops_report` drives the whole of `ops_claims.check_all` over a synthetic document twice per probe, so an uncached collection ran ~40 times a run and took the suite **75.4 s → 151 s**; cached it is 79.0 s, a net **+3.6 s**. Previously 3780 backend + tray (3752 + 28 on 2026-09-06, Session 190: 21 in `tests/test_ops_claims.py` and 7 in `tests/test_snag_claims.py::TestTheUnheldModuleCheck`, **none retired** — the deploy claim's population narrowed to the daemon's import graph, and the residue filed as `SNAG-SYSD-009` with the twenty-fifth check. **Twenty-one mutations driven and twenty-one killed — but three of them only after the test that should have caught them was repaired, and all three are the same class**: a clause whose removal changes no output. The `__pycache__` filter in `daemon_modules` is excluded by reachability anyway, so a stray file there was never a witness — the observable copy is in `sweep_sources`, and the unobservable one is pinned by a **statement** test, `abandoned_runs`' rule. The `create_app()` call in the new check adds **0** modules because `import sysadmin.main` already holds 95, so deleting it passed every behavioural drive including the subprocess one. And the ancestry clause was expected to be redundant and is not: dropping it loses **six** `__init__.py` files that no statement in this package names, which is package initialisation rather than the attribute-versus-module reading the first docstring claimed — reading the code gave the wrong answer where driving the mutation gave the right one. **The baseline was measured in a detached worktree rather than by stashing**: 110 in `test_ops_claims.py` against this cell's arithmetic, and 3752 + 28 = 3780 is arithmetic rather than a total read off a green run. **Four tests failed only under the whole suite** — other files import the review modules, which import the lazy module, so the new check's premise correctly refused to measure in a contaminated process; running the file alone never showed it, and the fixture that removes it now models the console-script process the check actually runs in. Previously 3752 backend + tray (3733 + 19 on 2026-09-06, Session 189: all 19 in the new `tests/test_close_reads_the_guard_gate.py`, the detector that outlives `SNAG-TEST-012`; **none retired** — no check was ever written for that entry, so closing it takes `convention:unchecked` 1 → 0 without a check retiring. Both shipped blocks are extracted between their own markers and driven **together**, because step 6 reads two variables step 3.8 sets and the defect lived in the join — 3.8 knowing something it did not pass on, and step 6 asserting health it had not seen. Seven readings of the gate crossed with the code-change count, at a stub gate in a throwaway repo. **Twelve mutations driven and eleven killed on the first attempt; one passed against deliberately broken code** — removing the status gate around the discriminator changed no output at all, because the finding branch is tested first at 3.8 and the green branch wins at step 6, so a red-suite reading at exit 1 is unobservable through both blocks. The clause is kept for `abandoned_runs`' reason and pinned by a **statement** test, the only kind that can reach a clause whose removal is invisible in behaviour. Three of the file's own first-draft tests were wrong and the drive said so: the stub premise looked for the marker prefix the block strips before printing; the structural pin found the gate's *prose* naming `coverage json` rather than its invocation; and the status gate's specimen was claimed to be this file, which carries the accessor and not the literal, so the premise moved to the producer. Baseline measured by collecting with the new file ignored — 3733 — so 3733 + 19 = 3752 is arithmetic rather than a total read off a green run. Previously 3733 backend + tray (3722 + 17 − 6 on 2026-09-06, Session 188: all 17 in the new `tests/test_close_runs_the_handoff_guard.py`, the detector that outlives `SNAG-TEST-005`; **6 retired** — `TestHandoffShapeUnguarded`, whose check retired with the entry. The guard is stronger than the check in an axis the sitting **got wrong in prose first**: it requires *both* `pytest` and `test_handoff_shape` on lines that run something, and the 2×2 was driven rather than reasoned — with the call deleted and the two advice echoes left, the retired either-name rule reads `mismatch`, **the mention rule alone still reads `mismatch`** (`if [ -x ".venv/bin/pytest" ]` is a real non-echo line), **requiring both names alone goes green** (the advice echo carries the second), and only the pair sees it — multiplicative rather than independent, `SNAG-AGENT-008`'s shape. Separable only at a stand-in, so `TestNeitherRuleCatchesTheRegressionAlone` is a recorded counterfactual and says so. **Nine mutations driven and nine killed**, each on its intended tests; the gate's three readings are driven at the **shipped block**, extracted between its own markers rather than retyped, against a stub `pytest` — because a test in `test_handoff_shape.py` that ran the close would recurse into itself, and the red reading is otherwise only reachable by mutating the live `HANDOFF.md`, which a concurrent session in this tree would see. **The baseline was measured by stashing to HEAD and re-collecting**: 3722, against **3651 in this cell** — 71 tests of Sessions 180–187 that never reached it, `SNAG-ESTATE-008`'s shape in this table's own cell again, which is why the arithmetic is carried rather than the total alone. Previously 3651 backend + tray (3590 + 61 on 2026-09-05, Session 179: 40 in `tests/test_vacuous_guards.py` and 21 in the new `tests/test_vacuous_guards_live.py`, **none retired** — `SNAG-TEST-009`'s runtime half. **Fourteen mutations driven and fourteen killed**, each on its intended tests, and two of them are the part worth carrying: the entry's own rule 1 reddens four, one of them the *live* drive, which is how a rule three sittings had written down was refuted; and the declaration anchor reddens four more, a defect that **shipped exit 0** because a stale declaration moves no verdict. The unit half pins the arc rules at hand-written arc sets and the live half runs the real `coverage run --branch` at 0, 1 and 2 iterations, `any`, `next` and both undecidable shapes — because the entry's own history (**110 → 43 → 26 → 23** findings) is a detector that returned a plausible number every time it was wrong, so a count cannot falsify one and a fixture with a known iteration count can. One live test asserts an **equality of arc sets** rather than a classification, with a decidable pair beside it as the control, because asserting the refusal would pass against a detector that refuses that shape for no reason. **The baseline was measured by stashing to HEAD and re-collecting**: 3590, against **3318 in this cell** — 272 tests of Sessions 154–178 that never reached it, `SNAG-ESTATE-008`'s shape in this table's own cell again and the widest gap it has shown, which is why the arithmetic is carried rather than the total alone. **Three reds were self-inflicted and only the arithmetic explained them**: the baseline stash ran *while the gate was collecting*, so the gate ran the pre-edit file, and 3611 + 36 = 3647 reconciled it exactly — the `stash-pop-reports-a-restart-owed` memory's hazard arriving at collection rather than at mtime. Previously 3318 backend + tray (3297 + 21 on 2026-09-02, Session 153: all 21 in `tests/test_snag_claims.py::TestTheStaleRungCheck`, **none retired** — the nineteenth check, for `SNAG-AGENT-012`. **Fourteen mutations driven and fourteen killed, each on its intended test — but one passed against every test in the class before the premise was repaired**: a drive aimed at `_refresh_open`, one level below the fork where the fix may land, which supplies its own `raised = 0` because the author put the standing row there. `_suppressed` is the witness that separates the two entry points, and `_refreshed` had to come **out** of that premise — it lives inside `_refresh_open`, so `step_for`'s shape leaves it at zero with the hold plainly fired and the check reported `unknown` over a landed fix, which only the fix-modelling stand-in could have said. Two further weak tests were repaired before mutation: an assertion that existed only to name the check key, and a before/after count of trigger rows that is **constant here whatever the drive does**, since a test process cannot reach `log_entries` under `sysadmin.service` at all — replaced by the observable mechanism, whether the record reaches a root handler. **One pre-existing red was repaired and it is not counted as an addition**: `tests/test_quietened_judgement_live.py` asserted the run's **box-wide** resolve count where it meant its own two titles, so it was red exactly while an editor held 3110/8110 — verified pre-existing by stashing to HEAD before blaming this sitting, and the scoped form still turns red under a modelled resolve-and-re-raise. **The baseline was measured by stashing to HEAD and re-collecting**: 3298 collected, which reconciles with this cell's 3297 passed + 1 skipped, so the row was right for the second sitting running. 3318 passed + 1 skipped = 3319 collected. Previously 3297 backend + tray (3285 + 12 on 2026-09-02, Session 152: all 12 in the new `tests/test_live_drive_scoping.py`, **none retired** — the guard that outlives `SNAG-TEST-004`, refusing a box-wide process selector in any `tests/test_*_live.py` drive. **Seven mutations driven and seven killed**, each on its intended test, the first two being the two real pre-fix calls put back into `test_notify_guard_live.py`. Two things only running it could have said: the detector **reports its own file**, not from its stand-in sources — those are strings, and a string is prose — but from its *expected values*, since `== ["pkill"]` and an argv list are spelled identically, which is the mirror of the prose problem arriving inside the fix for it; and the pre-fix specimen's assertion was written in the wrong order, because the walk sorts by line and the `pkill` is at 138 while both `pgrep`s are at 372 and 383. **The baseline was measured by stashing to HEAD and re-collecting**: 3286 collected against this cell's 3285, which reconciles — 3285 passed + 1 skipped — so for once the row was right and the arithmetic says so rather than being trusted. 3297 passed + 1 skipped = 3298 collected. Previously 3285 backend + tray (3276 + 9 on 2026-09-02, Session 151: 8 in `tests/test_service_recommendations.py::TestTheStepCanBeSuperseded` and 1 in `tests/test_health_review.py`, none retired — one of the nine **written twice**, because the first version drove a lone `timer_failed` row and asserted it kept its own step, which no implementation can get wrong: `recommend` never calls `_folded_row` on a group of one. The discriminating form declares `outage` superseding and reads the **detail**, since `action` comes out identical either way. **Nine mutations driven and nine killed**, each on the intended test — and two of them exist only because a first pass left two tests unreached: the subject-keyed implementation the entry's own wording points at, killed solely by `pgbackrest-backup-timer`, and a `RATE_ARGUED` kind declared superseding, which is a rule with no path to it. **The baseline was measured by stashing to HEAD and re-collecting**: 3276 + 1 skipped, against **3249 in this cell** — 27 tests of Sessions 147–149 that never reached it, `SNAG-ESTATE-008`'s shape in this table's own cell again, and the reason the arithmetic is carried rather than the total alone. Previously 3249 backend + tray (3264 − 19 + 4 on 2026-09-01, Session 146: 4 added in `tests/test_arbitrated_stops_live.py::TestTheDeployedQuieteningLive`, **19 retired** — `TestTheNightlyHoldCheck`, whose check retired with `SNAG-AGENT-011`. The guard did not retire with them and is **stronger than what it replaces in a named axis**: limb 1 rebuilt its window from `venture-enrich-nightly.timer`, keying this repository's guard on another project's schedule — which moved 02:00 → 00:00 on 2026-08-25 — while the re-homed tests read `details['arbitration']`, the blob the fix writes, and hold at any hour. **Five stand-ins driven and each reddens exactly its own test**: an arbitrated stop left `critical`, an `unread` row quietened, an unclassifiable reading, the fix as deployed (reddening none) — and the pre-fix world, which reddens **only the anti-vacuity pin** while the two behavioural tests *skip*, so without that pin a box that never deployed the fix reads green. One test is skipped by design and says so: the over-quietening direction has an empty population on a healthy box, and asserting the *absence* of a quietening is the direction a fix of this shape fails in. Arithmetic checked against the measured baseline rather than the cell: 3264 − 19 + 4 = 3249 = 3248 passed + 1 skipped. Previously 3230 + 34 on 2026-08-31, Session 145: 25 in the new `tests/test_arbitrated_stops.py`, 7 in the new `tests/test_arbitrated_stops_live.py` and 2 in `tests/test_import_boundary.py`; **none retired**, and one existing test **inverted rather than deleted** — `TestTheNightlyHoldCheck`'s live drive, which asserted `match` and now asserts `mismatch` **plus the reason**, because `SNAG-AGENT-011`'s check refutes on the commit by its own design and a test still demanding `match` pins the defect as the contract. **Fourteen mutations driven and fourteen killed**, each on the intended tests, plus two against the live half — and the pair that matters is `ARBITRATED_STOP_SEVERITY`: swapping it for the judge's constant (right value, wrong provenance) reddens only the import guard, and setting it to `warning` (wrong value) reddens only the pin, which is the value-versus-provenance split this file has recorded three sittings failing to make. **One restore was masked by the bytecode cache** — `stopped_units` → `units_stopped` is a *same-length* rename, so a repaired tree went on failing until `__pycache__` was cleared; the kills are unaffected, since a stale cache can hide a restore and never manufacture a red. The baseline was **3230 and this row was right**, the second time in six sittings. Previously 3230 backend + tray (3228 + 2 on 2026-08-31, Session 144: both in `tests/test_services_registry.py` — the widened declaration set and the live witness that a declared source really writes JSON — plus one existing premise in `tests/test_message_backfill_live.py` **relaxed rather than deleted**, because it stated the anti-vacuity premise and the dying only-one-source fact in one assertion. Three falsifications driven, each red on its own test: removing the new name, declaring `format: json` on the `print()`-based `estate-broker-provision` (red at 13 records read, 0 JSON-shaped), and undeclaring the probe unit. **The row this replaces read 3209 and the tree collected 3228 at `263c160`** — measured by running before a line was edited, so the 19-test gap is earlier sittings' additions that never reached this cell: `SNAG-ESTATE-008`'s shape in this table's own cell again, and the reason the arithmetic is carried rather than the total alone. Previously 3209 backend + tray (3196 + 13 on 2026-08-31, Session 142's follow-on: all 13 in the new `tests/test_handoff_shape.py`, none retired. Twelve guard `HANDOFF.md`'s two shape rules against estate-manager's `roadmap.py` — asserted as properties of **this document** rather than as a copy of their parser's logic — and the thirteenth sweeps `scripts/*.sh` for the execute bit, written after `30bfbea` shipped `claude-preflight.sh` at mode 0644 and a **mode is not content**, so the suite, ruff and the pre-commit hook were all green over the one script every sitting starts with. Four falsifications driven, each red on the intended test. Previously 3196 backend + tray (3180 + 48 − 32 on 2026-08-31, Session 142: 33 in the new `tests/test_gpu_lease.py`, 6 in the new `tests/test_gpu_lease_live.py` and 9 in `tests/test_gpu_gate_invocations.py`; **32 retired** — `TestTheReviewSlotCollisionCheck` and `TestTheReviewChainDrainCheck`, whose two checks retired with `SNAG-SCHED-001` and `SNAG-SCHED-003`. The guard did not retire with them and is **stronger than what it replaces**: those checks swept `sysadmin/` for any mention of an arbitrating name — weak enough that a docstring nearly satisfied one — while `TestTheWaiterlessInvocationTakesALease` asks, per review module, that the job acquires a lease, passes `gpu_lease_held`, and releases from a `finally`. The middle assertion is the load-bearing one: a job that took a lease and let the flag default to `False` would wait for the card and *then* give up on it, which is strictly worse than not waiting and green in every behavioural test, because both paths store a review. **Thirteen mutations driven and thirteen killed**, each on the intended tests and none passing against broken code — but one new test is a **recorded counterfactual rather than a guard and says so**, the copied-1800 arithmetic being over two constants that no code change can break. The baseline was measured by stashing to HEAD and re-collecting rather than read off this cell: 3180, which is what this row said, the first time in five sittings it has been right. Previously 3180 backend + tray (3160 + 20 on 2026-08-30, Session 140: six in `tests/test_snag_claims.py::TestTheReviewSlotCollisionCheck` for `SNAG-SCHED-002` and fourteen in the new `TestTheReviewChainDrainCheck` for `SNAG-SCHED-003`, none retired. Eleven mutations driven, each red on exactly the intended tests — and **one passed against deliberately broken code**: replacing the majority rule with unanimity survived, because the specimen for *"one slot inside is enough"* had that slot at **6 of 6**, a reading a majority rule and a unanimity rule agree about, so it witnessed neither; it is **4 of 6** now with a boundary test at exactly half. A second guard had to be strengthened before it was driven — the threshold pin compared the detail against `get_config()`, which passes just as well over a hard-coded `25` while the shipped threshold happens to be 25, so it **moves** the threshold and requires the reading to move with it: a value asserted where provenance was meant, for the third time in this file. **The row this replaces read 3107 and the tree collected 3160 at HEAD** — measured by stashing before a line was edited, so the 53-test gap is four sittings of additions that never reached this cell: `SNAG-ESTATE-008`'s shape in this table's own cell for the **third** time, and the reason the arithmetic is carried rather than the total alone. Previously 3107 backend + tray (3079 + 33 − 5 on 2026-08-30, Session 136: 26 in the new `tests/test_config_keys.py`, 4 in `tests/test_reload.py` and 5 in `tests/test_snag_claims.py::TestTheTraySectionCheck`; **five retired** — `TestTheConfigExtrasCheck`, whose check retired with `SNAG-CFG-004`. Twelve mutations driven, each red on the tests about its own rule, and **two passed against deliberately broken code first**: the subtree-exemption mutation changed nothing because `notifications.tray` is not itself in `FOREIGN_KEYS`, so the faithful version had to replace the constant *and* the matcher; and adding `ConfigDict(extra="forbid")` to a config model gave a **collection error** rather than a red test, because that name is not imported in that module — a stand-in that cannot compile is silence wearing a result. Baseline taken by running, not by reading. Previously 3079 backend + tray (3070 + 10 − 1 on 2026-08-30, Session 135: five in `tests/test_config_defaults.py::TestTheVacatedReviewLeavesStayGone` and five in `tests/test_snag_claims.py::TestTheConfigExtrasCheck`; **one retired** — `test_review_schedule_holds_and_is_refuted_by_a_reader`, which drove the check that retired with `SNAG-CFG-002`. Nine mutations driven, each red on exactly one intended test. **The row this replaces read 3018 and the tree collected 3070 at HEAD** — measured before a line was edited, so the 52-test gap is four sessions of additions that never reached this cell: `SNAG-ESTATE-008`'s shape in this table's own cell for the second time, which is why the arithmetic is carried and not the total alone. The gap is *why* the baseline is taken by running rather than by reading — had 3018 been trusted, `baseline + added == total` would have reported a clobber that did not happen. Previously 3018 backend + tray (3017 + 1 on 2026-08-30, Session 130: one leak guard in `tests/test_desktop_store_live.py`, none retired — counted by stashing to HEAD and re-collecting, 3017 → 3018. **The six reds are gone and no code changed to remove them**: `SNAG-TRAY-010` was the drive leaving `dnd_manager` reading the real wall clock, so the file was red inside the shipped `23:00 → 07:00` window and green outside it — Session 129 ran at 05:27. Three mutations driven, each red on exactly one intended guard, and the third found the drive **erroring** rather than failing at a different gate, which takes the premise test down before it can name the cause. Previously 3017 backend + tray (2984 + 33 on 2026-08-30, Session 129: all 33 in `tests/test_estate_judgements.py` for the `wiring` family, none retired. Counted by stashing to HEAD and re-collecting — 2984 → 3017 in the tree and 90 → 123 in the file, both deltas 33, which is the only arithmetic that can witness a clobber. **Twelve mutations driven and twelve killed, one of them only after the test was strengthened**: the `code`-is-never-read test asserted a true premise and a true consequence and could distinguish nothing, because the recorded findings carry no `code` at all, so a code-reading judge agrees with a detail-reading one by accident — a constant observation is not evidence unless something in the population would have forced a different one. **Six are red and none of them are this sitting's**: `tests/test_desktop_store_live.py`'s adoption drive fails at HEAD too, verified by stashing, with its own premise test passing and no leaked probe rows in `alerts` or `desktop_notifications` — filed as `SNAG-TRAY-010` rather than fixed here. Previously 2984 backend + tray (2971 + 13 on 2026-08-29, Session 128: 5 in `tests/test_unit_ports.py`, 5 in `tests/test_estate_judgements.py` and 3 in `tests/test_snag_claims.py`, none retired — one existing test **inverted** rather than deleted, because it pinned the check limb this sitting removed. Ten mutations driven, each red on exactly one intended test, and **one falsification passed against deliberately broken code**: the missing-key test drove a blob carrying no `ok` either, so the `ok` gate returned before the branch it names was reached and the mutation survived; it asserts the right value for the wrong reason until a successful-sweep-with-no-key specimen isolates it. **The row this replaces read 2937 and the tree collected 2971** — measured by stashing to HEAD and re-collecting rather than trusting the green, since `baseline + added == total` is the only arithmetic that can witness a clobber; the 34-row gap is `SNAG-ESTATE-008`'s shape in this table's own cell, so the figure here is now the measured one. Previously 2937 backend + tray (2899 + 38 on 2026-08-29, Session 126: 26 in `tests/test_failure_replay.py`, 5 in the new `tests/test_failure_replay_live.py` and 7 unit-file guards in `tests/test_systemd_units.py`, none retired. Eleven mutations driven, each red on exactly one intended test — and **one falsification passed against deliberately broken code, in the harness rather than the subject**: the stand-in notification server printed `claimed` and owned nothing a millisecond later, because a `dbus.service.BusName` held only in a local is garbage-collected on return, so the wait reported `False` after a full budget and that read as a verdict about the module. The first repair was insufficient the same way — it asserted the stand-in had *said* `claimed`, which the mutation satisfies. The premise asks the **bus** with `busctl` now, independent of both the subject and the harness, and the mutation fails naming the harness. Session 125's trap was avoided by construction: a guard mutated to refuse everything turns three live tests red and skips none. The count was verified by arithmetic against the baseline rather than by the suite being green. Previously 2886 + 13 on 2026-08-29, Session 125: six static guards in `tests/test_systemd_units.py` and seven live ones in the new `tests/test_notify_guard_live.py`, none retired. Eight mutations driven, each red on exactly one intended test — and **one passed against deliberately broken code**: a guard mutated to refuse everything left `test_it_admits_the_live_bus` *skipping* rather than failing, because its own skip predicate asked the guard under test whether a live notification server existed. A control a broken subject can switch off is not a control; it asks `busctl` directly now, and re-driven the mutation turns it red. The count was verified by arithmetic against a stashed HEAD rather than by the suite being green. Previously 2872 + 14 on 2026-08-29, Session 124: `TestTheReloadCoherenceCheck`'s thirteen members in `tests/test_snag_claims.py` and the specimen-does-not-install pin in `tests/test_config_defaults.py`, none retired. Nine mutations driven, each red on exactly one intended test — and **one passed against deliberately broken code**: reading the installed-witness back from the specimen instead of the singleton is the same number whenever the reload installs, and the surviving mutation named the missing case, a reload that reports success and installs nothing. Four of the stand-ins had to be rewritten to call through to the real drive first, because a stand-in that reports a verdict without installing the configuration models no fix at all. Previously 2869 + 3 on 2026-08-29, Session 123: `TestTheDuplicateIngestCheck`'s three new members in `tests/test_snag_claims.py` — the verdict keyed on the entry's narrow key, a divergently-parsed duplicate named rather than silent, and the record identity asserted at the statement because today both keys agree over 235,230 rows. None retired; the four existing members were re-driven at a fourth `query_one` call. Four mutations, each red on one intended test, and one of them passed against broken code first time — the equal-count case was uncovered. Previously 2863 + 6 on 2026-08-29, Session 122: `TestACutTitleStaysAnIdentity` in `tests/test_log_alert_dedup.py` and the estate parser's new raise shape in `tests/test_snag_claims.py`, none retired — one falsified against the pre-fix title and four against mutations of the fix, because a test that passes against the broken code is a control over the fix's failure modes rather than over the defect's. Previously 2844 + 19 on 2026-08-29, Session 120: the derived movement line and the closure-aware banner reader in `tests/test_snag_claims.py`, none retired — nine mutations driven, each red on the intended test. Previously 2838 + 6 on 2026-08-28, Session 119: the reminder-ceiling guard in `tests/test_config_defaults.py`, none retired. **This row was a session stale when that was written** — it read 2832 while Session 117's block read 2838, so the row and the block disagreed about the same figure in one file, which is `SNAG-ESTATE-008`'s shape and the reason the arithmetic is carried rather than the total alone. Previously: 2801 + 53 − 22 on 2026-08-28 for `SNAG-LOG-008`, then 2832 + 26 − 20 for Session 117's `SNAG-ESTATE-010`.))))))))))))))* 
| CI | 🟢 Complete | GitHub Actions: ruff + mypy-clean codebase + full pytest (headless Qt) |
| LLM | 🟢 Complete | llama.cpp (llama-server :8081, OpenAI-compatible API) — migrated from Ollama 2026-07-24 |
| Frontend | 🔴 Retired | Web UI died with PA (2026-07-24). The PyQt6 tray dashboard is now the only UI — see ideas.md for rebuilding it in Alfred's Nuxt frontend |

---

## Recently Completed

### Session 374 — on 7.2.9 the card sleeps, and the screens did not come back (2026-10-15)

- The unclean power-off at 2026-10-14 05:41 was not a hang. The card
  had slept all night with Steam quit; it woke at 05:19:10, no DP
  monitor reconnected, and the owner pressed and then held the power
  key. 7.2.7 never let the card sleep (0 resumes in a week); 7.2.9
  does (1,797 in one boot). Session 349's "where the card never
  sleeps" below held only until that upgrade. Pinning the card awake
  with a udev rule is the owner's step (tasks.md, Session 374).

### Session 368 — an empty database reaches head by the chain (2026-10-14)

- `tests/test_schema_build.py` is contract §2.7's test: a scratch
  database built from empty by `alembic upgrade head`, at the packaged
  head by `schema_status`, 0 drift against the models, then dropped.
  Skips without PostgreSQL, so CI does not run it yet.

### Session 356 — a web page can no longer fire the monitor's actions (2026-10-10)

- `require_auth` refuses with 403 a request whose `Origin` is set and
  not in `service.cors_origins`, on all 13 mutating routes, with or
  without a token. This closes the cross-site half of `SNAG-API-005`.
  The token half (`LoadCredential=`) is still open.
- Live since the owner's restart at 2026-10-10 16:52:34.

### Session 349 — the dGPU hunt is closed: 7.2 keeps the card awake (2026-10-08)

- One `linux-lts` night (6.18.55) with Steam quit: the card was
  suspended in 551 of 657 minutes, so the 7.2 kernel is what holds it
  awake. But at its two morning resumes no DP monitor reconnected (they
  woke to their logo, then black) and the owner hard-reset the box. The
  owner ruled on 2026-10-08 to close the hunt: the box stays on 7.2,
  where the card never sleeps and the screens always wake.

_Sessions 10–344 are in [archive/status_completed_2026-10-19.md](archive/status_completed_2026-10-19.md); Sessions 1–9 in [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md)._

---

## Notes

- Port 8500 (overridden from spec's 8100)
- Schema isolation: sysadmin.alembic_version avoids collision with PA
