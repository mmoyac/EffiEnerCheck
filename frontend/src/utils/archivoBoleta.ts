/** El navegador solo dibuja como imagen JPG, PNG y WEBP: un PDF (o un HEIC) se abre aparte. */
export const esImagenVisible = (url: string): boolean => /\.(jpe?g|png|webp)$/i.test(url)
