# Purdue CS Instagram source search — 2026-10-25

Scope: Purdue West Lafayette computing organizations, with Purdue Indianapolis listed separately. The [Purdue CS department roster](https://www.cs.purdue.edu/student-experience/clubs-organizations.html) lists 27 West Lafayette organizations. This search confirms Instagram accounts for 19 of those 27 organizations, plus three ACM subgroups, Build Purdue, and the Indianapolis CS Club. An unresolved roster entry is not evidence that the organization lacks Instagram. Public profile posts were scanned with the project's Instaloader adapter at up to eight recent posts per account. The 45 posts from the four original accounts were already in Snowflake; the **154 newly captured posts across 20 accounts were also inserted into Snowflake**. The public-post capture files remain in `/tmp/snowflask-cs-discovery*.json` for audit.

## Existing Snowflake sources

| Organization | Handle | Current captured posts | Source |
| --- | --- | ---: | --- |
| Purdue Hackers | `purduehackers` | 10 | [Organization site](https://www.purduehackers.com/) |
| CS Undergraduate Student Board | `purdueusb` | 12 | [BoilerLink](https://www.boilerlink.purdue.edu/organization/csusb) |
| Hello World | `helloworldpurdue` | 12 | [Purdue announcement](https://engineering.purdue.edu/AAEFlightPlanNews/news/misc/hello-world-hackathon-seeking-mentors) |
| Build Purdue | `buildpurdue` | 11 | Existing project capture; CS department roster does not list it |

## Newly scanned public accounts and Snowflake posts

| Organization | Handle | Recent posts found | Source / note |
| --- | --- | ---: | --- |
| CS Women's Network | `cswnpurdue` | 8 | [Organization site](https://www.cs.purdue.edu/cswn/) |
| ML@Purdue | `mlpurdue` | 8 | [Organization site](https://www.mlpurdue.com/) |
| ACM SIGAPP | `purduesigapp` | 8 | [Organization site](https://sigapp.club/) |
| ACM SIGBots | `purduesigbots` | 8 | [Organization site](https://www.purduesigbots.com/contact) |
| ACM SIGGD | `purduesiggd` | 8 | [Organization docs](https://purduesiggd.github.io/SIGGD-Docs/about/) |
| BoilerMake | `boilermake` | 8 | [Purdue announcement](https://mailman.ecn.purdue.edu/archives/list/engr-boilerbuzz-list%40ecn.purdue.edu/thread/QT7R3M7DOOJS5FUFAJ2J7OJGEEMQGJPO/) |
| Hack the Future | `hackthefuturepurdue` | 8 | [Organization site](https://www.htfpurdue.org/) |
| InnovateHer | `innovateherhacks` | 8 | [Organization page](https://www.linkedin.com/company/innovateherhacks) |
| Launchpad | `launchpadpurdue` | 8 | [Organization site](https://www.launchpadpurdue.com/) |
| Web Dev Club | `purduewebdevclub` | 8 | [Organization Linktree](https://linktr.ee/purduewebdevclub); newest captured post is from 2022 |
| Competitive Programmers Union | `purduecpu` | 6 | [Current club site](https://purduecpu.com/); public posts identify Purdue CPU |
| Boiler Blockchain | `boilerblockchain` | 8 | [Organization Linktree](https://linktr.ee/BoilerBlockchain) |
| The Anvil | `anvilstartups` | 8 | [Organization site](https://www.anvilstartups.com/) links to Instagram |
| Purdue Solar Racing | `purduesolar` | 8 | [Organization Linktree](https://linktr.ee/purduesolarracing) links to Instagram |
| Space and Earth Analogs Research Chapter | `purdue_search` | 8 | [Organization Linktree](https://linktr.ee/purduesearch) links to Instagram |
| SIAM Student Chapter | `siampurdue` | 4 | [Purdue announcement](https://engineering.purdue.edu/ECE/Academics/Graduates/Announcements/opportunity-for-ece-graduate-students-and-postdocs) names handle |
| Purdue IEEE | `purdueieee` | 8 | [Organization site](https://purdueieee.org/) links to Instagram |
| Humanoid Robot Club | `humanoid.purdue` | 8 | [Organization site](https://www.humanoidrobot.club/) links to Instagram |
| RoboMaster Club | `boilerbots` | 8 | [Organization site](https://purduerm.org/) links to Instagram |
| Purdue Indianapolis CS Club | `csclub_purdueindy` | 8 | [Organization site](https://csclubindy.cs.purdue.edu/join/); different campus |

Total new public posts scanned and inserted: **154** across **20** accounts. A public request for the guessed handles `gwcpurdue` and `purduearc` returned no usable posts; neither handle is verified here.

## Future event evidence found in captions

| Event | Date | Instagram source | Verification |
| --- | --- | --- | --- |
| BoilerMake XIV | January 22–24, 2027 | [BoilerMake post](https://www.instagram.com/p/De18m7yRmbm/) | Post says January 22–24; [organizer site](https://boilermake.org/) supplies 2027. |
| InnovateHer Hackathon | February 13–14, 2027 | [InnovateHer post](https://www.instagram.com/p/DexAdvtoqIO/) | Year and dates appear in caption. |
| The Anvil Pitch Night | October 28, 2026, 6:30 PM | [Anvil post](https://www.instagram.com/p/De1sirVETEQ/) | Post says Wednesday; [organizer site](https://www.anvilstartups.com/) supplies date, time, and venue (MRGN 121). |
| The Anvil Startup Roundtable | January 22, 2027, 9 AM–4 PM | [Anvil post](https://www.instagram.com/p/Dd32EDEDdH4/) | Year, date, and time appear in caption; West Lafayette venue is still to be announced. |
| Purdue IEEE ANSYS Fluent workshop | October 27, 2026, 6–8 PM | [IEEE post](https://www.instagram.com/p/DesLeQAHzH6/) | Caption says Tuesday, October 27, BHEE 129; year inferred from October 19, 2026 post date. Confirm before publishing. |
| Purdue IEEE PCB layout workshops | October 31 and November 7, 2026, 3–5 PM | [IEEE post](https://www.instagram.com/p/DexrMkPgDnL/) | Caption lists Saturday October 24, 31, and November 7, BRNG 2280; October 24 is past. Year inferred from October 21, 2026 post date. Confirm before publishing. |
| Carve & Code, Purdue Indianapolis | October 27, 2026, 5:30–7 PM | [CS Club post](https://www.instagram.com/p/De2_2uChdZV/) | Caption says Tuesday 10/27; year follows from the October 23, 2026 post date and weekday. Confirm before publishing. |

Other recent event posts include dates without a year or details only on a flyer. The caption-only extraction deliberately leaves those unconfirmed. The new posts **are in Snowflake**, but these accounts have no curated club mappings, so this scan published **zero new events**. Reviewed club mappings and event evidence are the next step before these events appear in the app.

## Roster entries without a verified Instagram handle in this pass

CS Graduate Student Association; central Purdue ACM account; Association of Multicultural Computer Scientists; Autonomous Robotics Club; b01lers CTF; Girls Who Code Purdue College Loop; Purdue Linux Users Group; Upsilon Pi Epsilon.

The [Purdue CS roster](https://www.cs.purdue.edu/student-experience/clubs-organizations.html) is the baseline for checking these names. Absence from this scan does not mean an organization lacks an Instagram account.
