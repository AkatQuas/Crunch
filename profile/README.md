# Customize MainMenu and Layout

1. Create a branch new App with MainMenu.nib contained if use different version of [Platypus](https://sveinbjorn.org/platypus), current is 5.5.0.\
   Version difference leads to different structure for MainMenu.nib

2. In case you have to use an branch new MainMenu.nib, first bundle the default MainMenu.nib into the XXX.app, which be created by Platypus inside XXX.app/Contents/Resources.

3. Drag that out and edit with XCode, mainly update the `WebviewOutputWindow` property and size. The images in our html files are displayed as 390 x 190 , make it beautiful. Disable resize!

4. Drag the new `MainMenu.nib` into the assets of Platypus profile and create the new XXX.app.

---

[Crunch](./Crunch.platypus) is for bundle on an Apple ARM device.

[Crunch.legacy](./Crunch.legacy.platypus) is for intel x86 Mac, legacy device.
