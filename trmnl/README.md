# TRMNL E-ink Display Plugin

Display NBA game recommendations on your TRMNL e-ink device.

## Quick Setup

1. Deploy main app to Railway (see main README)
2. In TRMNL account: Create Private Plugin with "Polling" strategy
3. Set endpoint: `https://your-app.railway.app/api/trmnl?days=7&team=LAL`
4. Copy markup from `trmnl/src/full.liquid` (or other layouts)
5. Set refresh to 3600 seconds (1 hour)
6. Add to TRMNL playlist

## Layouts

Copy one of these to TRMNL markup editor:
- `src/full.liquid` - Full screen
- `src/half_horizontal.liquid` - Half screen (horizontal)
- `src/half_vertical.liquid` - Half screen (vertical)
- `src/quadrant.liquid` - Quarter screen

## URL Parameters

```
https://your-app.railway.app/api/trmnl?days=7&team=LAL
```

- `days` - Lookback period (1-14, default: 7)
- `team` - Favorite team code (LAL, BOS, GSW, etc.)

## Local Development

```bash
cd trmnl
gem install trmnlp
trmnlp serve
# Open http://localhost:3000
```

## Common Team Codes

LAL, BOS, GSW, MIA, CHI, NYK, BKN, PHI, MIL, PHX

## Resources

- [TRMNL Docs](https://docs.usetrmnl.com/go/)
- [Liquid Templates](https://help.usetrmnl.com/en/articles/10671186-liquid-101)
