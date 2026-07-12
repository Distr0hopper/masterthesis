import { ApiProperty } from '@nestjs/swagger';
import { Transform } from 'class-transformer';
import { IsIn, IsOptional, IsString, IsUrl } from 'class-validator';
import { VALID_DOMAINS } from '../enums';

const emptyToUndefined = ({ value }: { value: unknown }) => (value === '' ? undefined : value);

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
  authorName?: string;

  @ApiProperty({ required: false, example: 'https://github.com/movestore/RemoveOutliers' })
  @Transform(emptyToUndefined)
  @IsOptional()
  @IsUrl()
  repoUrl?: string;

  @ApiProperty({ required: false, example: 'abc1234' })
  @IsOptional()
  @IsString()
  repoCommitSha?: string;

  @ApiProperty({
    required: false,
    nullable: true,
    example: null,
    description: 'Overrides the description extracted from the CWL file. Omit or set to null to use the extracted value.',
  })
  @IsOptional()
  @IsString()
  description?: string | null;
}