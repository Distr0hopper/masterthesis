import { ApiProperty } from '@nestjs/swagger';
import { IsIn, IsUrl } from 'class-validator';
import { VALID_DOMAINS } from '../enums';

export class PackageComponentDto {
  @ApiProperty({ example: 'https://github.com/movestore/RemoveOutliers' })
  @IsUrl()
  repoUrl: string;

  @ApiProperty({ enum: VALID_DOMAINS })
  @IsIn(VALID_DOMAINS)
  domain: string;
}