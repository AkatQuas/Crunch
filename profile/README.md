# Customize MainMenu and Layout

1. Create a branch new App with MainMenu.nib contained if use different version of [Platypus](https://sveinbjorn.org/platypus), current is 5.5.0.\
   Version difference leads to different structure for MainMenu.nib

2. In case you have to use an branch new MainMenu.nib, first bundle the default MainMenu.nib into the XXX.app, which be created by Platypus inside XXX.app/Contents/Resources.

3. Drag that out and edit with XCode, mainly update the `WebOutputWindow` (Web View) size. The web view and HTML content are **390 × 190** points. Disable resize!

   Source of truth: `profile/MainMenu.nib/designable.nib` (Interface Builder XIB). `make sync-app` compiles it into `bin/Crunch.app` with `ibtool`.

4. Drag the new `MainMenu.nib` into the assets of Platypus profile and create the new XXX.app.

---

[Crunch](./Crunch.platypus) is for bundle on an Apple ARM device.

[Crunch.legacy](./Crunch.legacy.platypus) is for intel x86 Mac, legacy device.
