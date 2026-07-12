import { ApiProperty } from '@nestjs/swagger';
import { IsIn, IsOptional, IsString, IsUrl } from 'class-validator';
import { VALID_DOMAINS } from '../enums';

export class PackageComponentDto {
  @ApiProperty({ example: 'https://github.com/movestore/RemoveOutliers' })
  @IsUrl()
  repoUrl: string;

  @ApiProperty({ enum: VALID_DOMAINS })
  @IsIn(VALID_DOMAINS)
  domain: string;

  @ApiProperty({
    required: false,
    nullable: true,
    example: null,
    description: 'Overrides the description extracted from metadata.json. Omit or set to null to use the extracted value.',
  })
  @IsOptional()
  @IsString()
  description?: string | null;
}