from core.image import RenderImage

profile = 'default'
r = RenderImage(profile)

r.generate('Tracks')
r.generate('Speed')
r.generate('Clicks')
