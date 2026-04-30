Team banner PNGs.

The filename suffix describes which DISPLAY SIDE of the scoreboard the
banner is meant to appear on, not which role the team has in the game:

  <ABBR>_HOME.webp   shown on the LEFT side of the scoreboard
                    (used when this team is the AWAY/visiting team)

  <ABBR>_AWAY.webp   shown on the RIGHT side of the scoreboard
                    (used when this team is the HOME/hosting team)

  <ABBR>.webp        legacy fallback - used if neither side-specific
                    file exists. Existing files keep working.

Examples for a Rangers @ Sabres game:
  NYR_HOME.webp      shown on the LEFT  (NYR is the away team)
  BUF_AWAY.webp     shown on the RIGHT (BUF is the home team)

For a Sabres @ Rangers game (sides swap):
  BUF_HOME.webp      shown on the LEFT  (BUF is the away team)
  NYR_AWAY.webp      shown on the RIGHT (NYR is the home team)

Recommended size: 2172x724 (3:1 ratio). Other ratios work too -
the renderer auto-fits the row height to the artwork's natural aspect.

Resolution priority:
  1. side-specific file (HOME/AWAY suffix per the convention above)
  2. generic <ABBR>.png
  3. fallback colored rectangle with abbreviation text

