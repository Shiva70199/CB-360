import Image from "next/image";

const LOGO_RATIO = 826 / 539;

export function BrandMark({ height = 40 }: { height?: number }) {
  const width = Math.round(height * LOGO_RATIO);
  return (
    <Image
      src="/cb360-logo.png"
      alt="CB 360"
      width={width}
      height={height}
      priority
    />
  );
}
