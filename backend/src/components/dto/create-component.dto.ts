import { ApiProperty } from '@nestjs/swagger';
import { IsIn, IsOptional, IsString, IsUrl } from 'class-validator';
import { VALID_DOMAINS } from '../enums';

export class CreateComponentDto {
  @ApiProperty({ example: 'My EO Component' })
  @IsString()
  name: string;

  @ApiProperty({ enum: VALID_DOMAINS })
  @IsIn(VALID_DOMAINS)
  domain: string;

  @ApiProperty({ required: false, example: 'Julius Arzberger' })
  @IsOptional()
  @IsString()
  author?: string;

  @ApiProperty({ required: false, example: 'https://github.com/movestore/RemoveOutliers' })
  @IsOptional()
  @IsUrl()
  repoUrl?: string;

  @ApiProperty({ required: false, example: 'abc1234' })
  @IsOptional()
  @IsString()
  repoCommitSha?: string;
}